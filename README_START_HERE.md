# เริ่มอบรมที่นี่ — UBE Safety Talk (ผู้เข้าอบรม)

**สำคัญ:** ชุดนี้คือจุดเริ่มต้น ไม่ใช่ระบบที่พัฒนาเสร็จแล้ว และไม่เชื่อมระบบ UBE จริง

## เตรียมเครื่อง Windows (VS Code + Python 3.11+)
1. แตก ZIP ไปที่โฟลเดอร์สั้น ๆ เช่น `C:\UBE_Workshop\UBE_Safety_Workshop` (หลีกเลี่ยง OneDrive/network path ชั่วคราว)
2. ติดตั้ง VS Code และ Python; ใน VS Code เปิดโฟลเดอร์ `UBE_Safety_Workshop` ด้วย File > Open Folder
3. เปิดไฟล์ `01_SETUP_WINDOWS.cmd` หรือใช้ Terminal: `py -3 -m venv .venv` แล้ว `.venv\Scripts\python.exe -m pip install -r requirements.txt`
4. เรียก `02_RUN_APP_WINDOWS.cmd` (หรือ `.venv\Scripts\python.exe -m streamlit run app.py`)
5. เปิด `http://localhost:8501` ถ้าเบราว์เซอร์ไม่เด้งขึ้นเอง
6. ใน VS Code ติดตั้งส่วนขยาย **Codex (OpenAI)** และลงชื่อเข้าใช้ด้วย ChatGPT; หากองค์กรบล็อก ให้ใช้คำแนะนำของผู้สอน/โค้ดสำรอง
7. เริ่มจาก `PROMPTS_คัดลอกใส่_Codex/00_README_PROMPTS.md` แล้ว copy ไปทีละไฟล์

## ไฟล์สำคัญ
- `AGENTS.md`: กติกาสำหรับ Codex (ช่วยคุมขอบเขต)
- `REQUIREMENTS_SAFETY_TALK.md`: Requirement จากชีต Safety Talk ใน Excel ของเจ้าหน้าที่
- `config/departments.json`: รายชื่อหน่วยงาน UBE/UBS ที่ถอดจาก Excel
- `data/sample_safety_talk.csv`: ข้อมูลสมมติสำหรับฝึก Dashboard
- `data/reports.csv`: ไฟล์ว่างสำหรับบันทึกแบบฟอร์มที่สร้างขึ้นใน workshop
- `app.py`: หน้าเริ่มต้นให้ Codex พัฒนาต่อ

## Checkpoint (ตามสไลด์)
- Slide 31–41: เปิด app.py ได้ + Codex เห็นโฟลเดอร์
- 42–58: มีเมนู/โครงสร้าง + ฟอร์มอิง Requirement
- 59–65: ฟอร์มตรวจ required fields และบันทึก CSV พร้อม Report ID
- 66–80: Dashboard + KPI + History + Filter
- 81–90: ผ่านการทดสอบครบและแก้ Error
- 91: สรุปงานที่ฝึกทำ ไม่ใช่การส่งมอบหรือ Deploy จริง

## ขอบเขต/ความปลอดภัย
- ใช้ข้อมูลตัวอย่างเท่านั้น ห้ามป้อนชื่อจริง/ข้อมูลอ่อนไหวของบริษัทโดยไม่ได้รับอนุญาต
- หลีกเลี่ยงการกดอนุญาตให้ Codex ลบไฟล์/ใช้เครือข่ายหรือรันคำสั่งที่ไม่เข้าใจ
- แสดงหน้าจอเว็บ/ทดสอบใน `localhost` เท่านั้น

## ไฟล์ตัวอย่างสำหรับทดสอบการแนบหลักฐาน
- `demo_evidence/DEMO_SAFETY_TALK_PHOTO.jpg`
- `demo_evidence/DEMO_SAFETY_TALK_IMAGE.png`
- `demo_evidence/DEMO_SAFETY_TALK_DOCUMENT.pdf`
- ทุกไฟล์มีคำว่า DEMO / TRAINING ONLY และไม่มีข้อมูลจริง

## ตารางตัวอย่างสำหรับเปิด Excel
- ไฟล์ `UBE_Safety_Talk_Training_Data.xlsx` อยู่ที่โฟลเดอร์เหนือโปรเจกต์หนึ่งระดับ มี Requirements, หน่วยงาน, ข้อมูลสมมติ และ Checkpoint
