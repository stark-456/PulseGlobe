"""
数据包存储服务
负责将采集的数据写入 data_packets 表
"""
import logging
from typing import Optional
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor, Json

from pulseglobe.core.config import get_config
from pulseglobe.models.data_packet import DataPacket

logger = logging.getLogger(__name__)


class PacketStorage:
    """数据包存储服务"""
    
    def __init__(self):
        config = get_config()
        db_config = config.database
        
        self.db_config = {
            "host": db_config.get("host"),
            "port": db_config.get("port"),
            "dbname": db_config.get("name"),
            "user": db_config.get("user"),
            "password": db_config.get("password"),
        }
        self._conn = None
    
    def _get_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self.db_config)
        return self._conn
    
    def save_packet(self, packet: DataPacket) -> Optional[int]:
        """
        保存单个数据包
        
        Returns:
            插入的记录ID，如果重复则返回None
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO data_packets (
                        session_id, source_type, source_detail,
                        keyword, keyword_type,
                        title, content, content_zh, summary,
                        url, author, publish_date, platform,
                        engagement, created_at, tags, content_hash
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (session_id, content_hash) DO NOTHING
                    RETURNING id
                """, (
                    packet.session_id,
                    packet.source_type,
                    packet.source_detail,
                    packet.keyword,
                    packet.keyword_type,
                    packet.title,
                    packet.content,
                    packet.content_zh,
                    packet.summary,
                    packet.url,
                    packet.author,
                    packet.publish_date,
                    packet.platform,
                    Json(packet.engagement),
                    packet.created_at,
                    packet.tags,
                    packet.content_hash,
                ))
                
                result = cur.fetchone()
                conn.commit()
                
                if result:
                    return result[0]
                return None  # 重复数据
                
        except Exception as e:
            logger.error(f"保存数据包失败: {e}")
            conn.rollback()
            raise
    
    def save_packets(self, packets: list[DataPacket]) -> dict:
        """
        批量保存数据包
        
        Returns:
            {"saved": int, "duplicates": int}
        """
        saved = 0
        duplicates = 0
        
        for packet in packets:
            try:
                result = self.save_packet(packet)
                if result:
                    saved += 1
                else:
                    duplicates += 1
            except Exception as e:
                logger.warning(f"跳过异常数据包: {e}")
                continue
        
        logger.info(f"[PacketStorage] 保存完成: {saved} 新增, {duplicates} 重复")
        return {"saved": saved, "duplicates": duplicates}
    
    def get_packets_by_session(
        self, 
        session_id: str,
        source_type: str = None,
        keyword: str = None,
        tags: list[str] = None,
    ) -> list[DataPacket]:
        """
        按条件查询数据包
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM data_packets WHERE session_id = %s"
        params = [session_id]
        
        if source_type:
            query += " AND source_type = %s"
            params.append(source_type)
        
        if keyword:
            query += " AND keyword ILIKE %s"
            params.append(f"%{keyword}%")
        
        if tags:
            query += " AND tags && %s"
            params.append(tags)
        
        query += " ORDER BY created_at"
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        
        return [DataPacket.from_dict(dict(row)) for row in rows]
    
    def get_session_stats(self, session_id: str) -> dict:
        """获取session统计信息"""
        conn = self._get_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source_type, COUNT(*) as count
                FROM data_packets
                WHERE session_id = %s
                GROUP BY source_type
            """, (session_id,))
            
            stats = {"total": 0}
            for row in cur.fetchall():
                stats[row[0]] = row[1]
                stats["total"] += row[1]
        
        return stats
    
    def get_summaries_for_outline(self, session_id: str) -> list[dict]:
        """
        获取用于生成大纲的摘要列表
        
        Returns:
            [{source_type, keyword, summary, url}, ...]
        """
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT source_type, keyword, summary, url, title
                FROM data_packets
                WHERE session_id = %s
                ORDER BY source_type, keyword
            """, (session_id,))
            
            return [dict(row) for row in cur.fetchall()]
    
    def close(self):
        """关闭连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
