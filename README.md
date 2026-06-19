# Automated Currency Exchange Rate Data Pipeline

### Project Overview
ระบบท่อส่งข้อมูล (Data Pipeline) สำหรับติดตามและวิเคราะห์ความผันผวนของอัตราแลกเปลี่ยนเงินตราต่างประเทศ (เทียบกับสกุลเงิน USD) 
ทำงานแบบอัตโนมัติทุกๆ 5 นาที ดึงข้อมูลสดจาก API สาธารณะ นำมาคำนวณสถิติเชิงลึก และสร้างกราฟรายงานสรุปแนวโน้มอัตโนมัติ

### Architecture Diagram

Exchange Rate API ──> Python ETL (Pandas) ──> SQLite Warehouse ──> Automated Visualization (Seaborn)
                             └──> Scheduled via Windows Task Scheduler

### Key Value & Features
* **Robust Error Handling:** ระบบมี Try-Except แยกส่วนชัดเจน หาก API ล่ม จะไม่ส่งผลกระทบต่อระบบฐานข้อมูล และมีการทำระบบ Logging บันทึกประวัติลงไฟล์อย่างเป็นระบบ
* **Data Value Enrichment:** ในขั้นตอน Transform ไม่ได้ทำแค่กรองข้อมูล แต่ใช้หลักการวิเคราะห์ทางสถิติเปรียบเทียบราคาปัจจุบันกับค่าเฉลี่ยในอดีต (AVG Windows) เพื่อสร้างระบบแจ้งเตือนทิศทางค่าเงิน (Market Signal) ได้แก่ Weakening, Strengthening หรือ Stable
* **Automated Historical Analysis:** ปรับปรุงระบบเป็น Incremental Load (Append) เพื่อเก็บประวัติ และส่งออกกราฟวิเคราะห์แนวโน้มความเคลื่อนไหวโดยอัตโนมัติ

### How to Run
1. ติดตั้งแพ็กเกจ: `pip install -r requirements.txt`
2. สั่งรันสคริปต์: `python src/intermediate_etl.py`
