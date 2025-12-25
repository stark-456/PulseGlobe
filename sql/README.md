# SQL 脚本目录

存放 PulseGlobe 项目的数据库脚本。

## 文件说明

| 文件 | 用途 |
|------|------|
| `migrate_to_pulseglobe.sql` | 数据迁移脚本（psql 变量版） |
| `migrate_simple.sql` | 简化版迁移脚本（手动修改日期） |

## 使用方法

### 方式一：VSCode 数据库插件

直接使用 `migrate_simple.sql`，手动修改脚本中的日期后执行。

### 方式二：psql 命令行

```bash
psql -h 111.91.20.199 -U postgres -d news_db -f migrate_to_pulseglobe.sql
```
