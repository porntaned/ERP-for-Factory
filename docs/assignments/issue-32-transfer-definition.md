# M4.3.1 — กำหนดข้อมูลรายการโอน

> Current status (2026-10-24): owner-merged [PR #33](https://github.com/porntaned/ERP-for-Factory/pull/33); M4.3 accepted through PR #45. See [closeout evidence](../evidence/m43-closeout.md). Pre-merge scope, exclusions and pending statements below are historical.

[Issue #32](https://github.com/porntaned/ERP-for-Factory/issues/32) ·
Repository `porntaned/ERP-for-Factory` · Branch `codex/docs/m431-transfer-contract`.
Base: `e698f29aaa381d6a353789beb956bc905905dc2f`.

**ขอบเขตที่เจ้าของสั่ง:** ทำเฉพาะข้อแรกของรายการ M4.3 ที่เสนอไว้ คือกำหนด
Lot, คลังต้นทาง–ปลายทาง, จำนวน และเหตุผล พร้อมห้ามโอนเข้าคลังเดิมหรือข้าม Plant
เอกสารนี้กำหนดสิ่งที่ระบบโอนในอนาคตต้องตรวจ ยังไม่ได้เพิ่มระบบโอนหรือการบังคับกฎใหม่
เจ้าของอนุมัติให้ส่งมอบและ Merge M4.3.1 เมื่อ 2026-10-23; M4.3 โดยรวมยังไม่เสร็จ
สถานะ Merge/CI ปัจจุบันดูที่ Issue #32 ซึ่งเชื่อม PR และ commit ที่ส่งมอบจริง

## ข้อมูลหนึ่งรายการ

ชื่อด้านล่างเป็นชื่อเชิงตรรกะสำหรับออกแบบ ยังไม่ใช่ API, model หรือ schema ที่สร้างแล้ว

| ข้อมูล | ความหมายและข้อกำหนด |
| --- | --- |
| `lot` | Lot เดิมที่บันทึกอยู่จริงหนึ่งรายการ อ้างด้วย identity ของแถว ไม่เลือกจาก code อย่างเดียว |
| `source_warehouse` | Warehouse เดิมที่มีอยู่จริง เป็นคลังที่ของออก |
| `destination_warehouse` | Warehouse เดิมที่มีอยู่จริง เป็นคลังที่ของเข้า ต้องคนละ identity กับต้นทาง |
| `quantity` | จำนวนที่ต้องการโอนเป็นบวก ใช้หน่วยหลัก `Item.base_uom` ของ Lot นั้น เป็น exact Decimal ที่ finite, น้อยกว่า `10^14`, แทนค่าได้ด้วยทศนิยมไม่เกิน 6 ตำแหน่ง |
| `reason` | ข้อความเหตุผลที่ไม่ว่างและไม่ใช่ whitespace ล้วน รองรับ Unicode เก็บข้อความเดิมรวมช่องว่างรอบข้อความ |

หนึ่งรายการมี Lot เดียวและคลังหนึ่งคู่ ไม่สร้าง Lot ใหม่ ไม่แยก/รวม Lot ไม่รับหลายบรรทัด
ไม่แปลงหน่วย และไม่เพิ่มข้อจำกัดประเภท Item ใหม่ในข้อย่อยนี้ ชนิดข้อมูลและชื่อ public API
สุดท้ายต้องล็อกใน Issue implementation ภายหลัง

## กฎข้อมูลที่จะต้องตรวจเมื่อพัฒนาระบบโอน

1. Lot และ Warehouse ทั้งสองต้องเป็น record ที่บันทึกและยังมีอยู่จริง ไม่รับ `None`,
   ชนิดผิด, unsaved object, unsaved object ที่ใส่ PK ชนแถวจริง หรือ ID ที่ไม่มีอยู่
2. `source_warehouse.pk != destination_warehouse.pk` ห้ามย้ายเข้าคลังเดียวกัน
3. Plant ID ปัจจุบันของคลังทั้งสองต้องเท่ากัน การอยู่ Organization เดียวกันอย่างเดียวไม่พอ
4. Organization ปัจจุบันของ `lot.item` ต้องตรงกับ Organization ของ Plant นั้น
   ตรวจจากข้อมูลที่ persist แล้ว ไม่อาศัย relation cache หรือชื่อ/code ที่ caller ส่งมา
5. จำนวนต้องเป็นค่าบวกในหน่วยหลัก ไม่รับศูนย์ จำนวนติดลบ `NaN`, infinity,
   ค่าตั้งแต่ `10^14` หรือค่าที่ต้องปัดเศษให้เหลือ 6 ตำแหน่ง
   `1.0000000` ยอมรับได้เพราะศูนย์ท้ายไม่เปลี่ยนค่า; `0.0000001` ต้องปฏิเสธ
   สำหรับขอบเขต Python ภายใน ใช้ Decimal ไม่แปลง float อย่างเงียบ ๆ
6. เหตุผลต้องเป็น string มีเนื้อหาอย่างน้อยหนึ่งตัวหลังตรวจ whitespace
   การตรวจว่าไม่ว่างไม่ใช่คำสั่งให้ตัดหรือเปลี่ยนข้อความที่จะเก็บ

ตัวเลขที่เป็นบวกนี้คือขนาดการโอน ไม่ใช่คำสั่งให้เพิ่มยอดทั้งสองคลัง ผู้ใช้ไม่ส่งค่า
`-quantity` แยกมาต้นทาง การสร้างรายการหัก–เพิ่มและการรักษายอดรวมอยู่ใน M4.3.4

## ตัวอย่างตรวจรับของสัญญา

ทุกตัวอย่างเป็นข้อมูลจำลอง คำว่า “ผ่านรูปแบบ” หมายถึงผ่านกฎข้อมูลใน M4.3.1 เท่านั้น
ยังไม่รับรองสิทธิ์, Quality, ยอดเพียงพอ หรือการบันทึกยอดจริง
สมมติ Lot L อยู่ Organization O1; Warehouse A/B อยู่ Plant P1 ของ O1

| กรณี | ผลที่ระบบโอนในอนาคตต้องให้ |
| --- | --- |
| L, A → B, Decimal `30`, เหตุผล “โอนเพื่อจัดเก็บ” | ผ่านรูปแบบ |
| เปลี่ยนทิศเป็น B → A แต่ยังเป็นคนละคลังใน P1 | ผ่านรูปแบบ ไม่เปลี่ยนเครื่องหมาย input |
| A → A หรือ object คนละตัวแต่ Warehouse PK เดียวกัน | ปฏิเสธคลังเดียวกัน |
| A → C ซึ่งอยู่ P2 ของ O1 | ปฏิเสธข้าม Plant แม้อยู่ Organization เดียวกัน |
| Warehouse code `A` ทั้งต้นทาง/ปลายทาง แต่คนละ Plant | ปฏิเสธข้าม Plant; ห้ามเทียบแค่ code |
| Plant code เหมือนกันแต่เป็นคนละ identity/Organization | ปฏิเสธข้าม Plant |
| Lot ของ O2 แต่ A/B อยู่ O1 | ปฏิเสธ Organization ไม่ตรง |
| Lot code เหมือนกันแต่คนละ Item | ต้องระบุ Lot identity ที่เลือก; ห้ามเดาจาก code |
| cached relation บอกว่า P1 แต่ฐานข้อมูลเปลี่ยนไป P2 | ใช้ identity ปัจจุบันและปฏิเสธถ้าข้าม Plant |
| Lot/คลังหายไป, `None`, unsaved หรือ unsaved ใส่ PK เอง | ปฏิเสธ input |
| จำนวน `0`, `-30`, `NaN`, infinity หรือ `100000000000000` | ปฏิเสธจำนวน |
| Decimal `0.0000001` | ปฏิเสธ precision; ห้ามปัดเป็น `0` |
| Decimal `0.000001`, `1.0000000`, `99999999999999.999999` | ผ่านรูปแบบจำนวน |
| จำนวนเป็น float `0.1` | ปฏิเสธที่ขอบเขต Python ภายใน; รูปแบบ transport ยังไม่กำหนด |
| reason เป็น `None`, string ว่าง หรือ whitespace ล้วน | ปฏิเสธเหตุผล |
| reason เป็น “  โอน LED ไปคลังสำรอง  ” | ผ่านรูปแบบและเก็บข้อความเดิม |

## ขอบเขตที่ต้องทำภายหลัง

- **M4.3.2:** กฎสิทธิ์ทั้งสองคลัง การตรวจ persisted active actor/grant ตอนเขียนจริง
  ข้อเสนอ `WAREHOUSE` ทั้งสองคลังยังต้องให้เจ้าของเลือก ไม่ถือว่าอนุมัติใน M4.3.1
- **M4.3.3:** Quality ของต้นทาง/ปลายทาง สถานะใดโอนได้และปลายทางมีสถานะใด
  ห้ามสรุปว่านโยบายรับเข้า HOLD ของ M4.2 ใช้กับการโอนโดยอัตโนมัติ
- **M4.3.4:** atomic debit/credit, ยอดต้นทางเพียงพอ, ลำดับ lock และ rollback
- **M4.3.5:** ประวัติ/ตัวตนผู้โอน/เวลา/การเชื่อม ledger สองฝั่ง
- **M4.3.6:** request identity และการชนกัน/คำขอซ้ำของการโอน ไม่ถือว่า UUID ของ receipt
  ป้องกัน transfer แล้ว และไม่ทำให้ M4.4 โดยรวมเสร็จ
- **M4.3.7:** tests PostgreSQL ของเส้นทางโอนจริงและ independent review ก่อน owner-review PR

ไม่เพิ่ม model, migration, service, endpoint, UI, tests, dependencies หรือ stock writes
ในงานนี้ ไม่มี Reversal, adjustment, valuation, real data, Manufacturing, PLC หรือ Deploy; Merge เฉพาะ PR เอกสารนี้ตามคำอนุมัติล่าสุด

## หลักฐานและ self-Scrutinize

ผู้ทำจริง: root เป็น manager/ผู้เขียนเอกสาร/self-review ไม่มีการอ้าง independent review
สำหรับเอกสารนี้ ไฟล์ที่อนุญาต: เอกสารนี้และ `docs/TASKS.md` เท่านั้น

ตรวจ Git ก่อนเริ่ม: origin ตรง repository, local สะอาดที่ `a762c2d`; `git fetch origin`
ยืนยัน main `e698f29` แล้วสร้าง feature branch จาก main ดังกล่าว GitHub ไม่มี Issue
เปิดค้างก่อนสร้าง #32; [main CI #107](https://github.com/porntaned/ERP-for-Factory/actions/runs/39911649403)
ผ่านหลัง Merge PR #31 หลักฐานนี้ยืนยัน baseline ไม่ใช่การทดสอบ transfer

Trace ที่อ่านจริง:

- [Facilities models](../../facilities/models.py): Warehouse มี Plant; Plant มี Organization;
  Warehouse code unique ภายใน Plant จึงใช้ code แทน global identity ไม่ได้
- [Catalog models](../../catalog/models.py): Item มี Organization และ base UOM
- [Inventory models](../../inventory/models.py): Lot code unique ภายใน Item;
  ledger ใช้ exact quantity/range/precision ตามกฎเดิม
- [Inventory services](../../inventory/services.py): มี balance snapshot และ receipt
  แต่ยังไม่มี transfer command; snapshot ไม่ใช่การจองของหรือสิทธิ์โอน

**Intent/smaller solution:** ล็อกเพียงสัญญาข้อมูลและตัวอย่าง แทนการเริ่มพัฒนา schema/API
ก่อนเจ้าของเลือกสิทธิ์/Quality **Verify:** ตรวจตัวอย่างกับ source จริงและตรวจ Markdown/diff
ไม่มีการอ้างผล business tests ใหม่ของ transfer **Verdict:** `ship` สำหรับ PR เอกสาร
หลังตรวจลิงก์และขอบเขต; เจ้าของอนุมัติ Merge แล้ว โดยต้องรอ CI ผ่านก่อน

Handoff: เมื่อสัญญานี้ผ่าน owner review งานถัดไปคือให้เจ้าของตัดสิน M4.3.2 และ M4.3.3
ก่อน implementation ที่เปลี่ยน stock ไม่มีการอนุมัติหรือเริ่มข้อถัดไปโดยเอกสารนี้

## Local verification — 2026-10-23

Windows PowerShell / Python จาก `.venv`: ตรวจ Markdown ทั้งสองไฟล์ด้วย
`pathlib`/`re` (local link targets, balanced fences และสถานะ checklist);
`git diff --check` ผ่าน ไม่มีการเปลี่ยน application หรือ tests
SHA ที่ทดสอบโดย CI จะอยู่ใน PR ที่เชื่อมกับ Issue #32; CI เดิมไม่ใช่หลักฐาน transfer implementation

## Delivery evidence

[PR #33](https://github.com/porntaned/ERP-for-Factory/pull/33) ส่งมอบเอกสารนี้
[contract commit](https://github.com/porntaned/ERP-for-Factory/commit/99486ddd7dbb94ff31735a223db1f6a02c520e82)
ผ่าน local Markdown checks: 2 files / 109 local targets / balanced fences และ
`git diff --check`; การติ๊ก M4.3.1 หมายถึงส่งมอบนิยามและเจ้าของอนุมัติแล้ว
สถานะ Merge และ CI final head ตรวจจาก PR นี้โดยตรง ไม่ใช่การรับรองระบบโอนจริง
