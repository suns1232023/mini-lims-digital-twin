# mini-lims-digital-twin
Interactive 3D/2D Digital Twin LIMS for Microbiology Lab monitoring, asset tracking, and sample workflow.
# Mini-LIMS 微生物学实验室数字孪生系统

> 基于 1:1 实验室物理空间布局构建的可交互、图示化数字孪生 Mini-LIMS 系统。集成空间可视化、设备与环境（温湿度/压差）实时态势感知、传递窗状态联动及 LIMS 样品流转全履历追踪。

---

## 🌟 核心特性 (Features)

* 🏢 **物理空间数字映射**：1:1 精确复刻万级洁净区、一更/二更/缓冲间、阳性对照室、无菌室及理化实验区。
* 📡 **IoT 实时态势感知**：实时采集并监控灭菌锅、百级工作台、生物安全柜、培养箱等设备的数据流与报警。
* 🚪 **传递窗与流程联动**：图示化监控传递窗连锁状态、UV 消毒及样品穿越洁净区的时空轨迹。
* 📊 **LIMS 业务可视化看板**：将传统的表格化 LIMS 数据转化为空间图示化交互看板。

---

## 🏗️ 系统架构与技术栈 (Tech Stack)

* **前端 (Frontend)**: Vue 3 + TypeScript + Three.js / Canvas2D + Tailwind CSS
* **后端 (Backend)**: Python (FastAPI) / Node.js (NestJS) + WebSocket
* **数据库 (Database)**: PostgreSQL (业务数据) + InfluxDB / TimescaleDB (时序数据) + Redis
* **IoT 通讯 (IoT/Protocols)**: MQTT / Modbus TCP

---

## 📂 项目结构规划 (Directory Structure)

```text
mini-lims-digital-twin/
├── docs/                 # 项目架构、设计文档与 API 规范
├── frontend/             # 前端数字孪生渲染与 UI 交互代码
├── backend/              # LIMS 核心业务逻辑与 API 服务
├── iot-gateway/          # IoT 传感器数据采集适配器与模拟器
├── assets/               # 实验室平面图纸、3D 模型与静态资源
└── docker-compose.yml    # 一键本地容器化部署配置
