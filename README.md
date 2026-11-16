# MacWin Bridge

[![Build macOS launchers](https://github.com/ozrugame/Macwin_bride/actions/workflows/build.yml/badge.svg)](https://github.com/ozrugame/Macwin_bride/actions/workflows/build.yml)

ตัวเปิด Windows Steam และเกมบน Apple Silicon Mac ผ่าน Wine + DXMT โดยใช้ Wine prefix และคลังเกมกลางเดียว ไม่ติดตั้ง Windows VM แยกตามเกม

**Repository นี้เป็นซอร์สและระบบ build ตัวเปิด** ยังไม่มีตัวติดตั้ง Wine/Steam/ไลบรารีกราฟิกอัตโนมัติสำหรับเครื่องใหม่ ต้องเตรียม runtime ตาม [ข้อกำหนด runtime](docs/RUNTIME.md) ก่อนเล่นเกม แพ็กเกจไม่รวมไฟล์เกม เซฟ บัญชี Steam หรือ runtime ที่ติดตั้งในเครื่องผู้พัฒนา

## Build

ต้องมี macOS, Swift 6, Xcode Command Line Tools, Python 3.9+ และ Homebrew สำหรับติดตั้งตัว cross-compiler:

```sh
git clone https://github.com/ozrugame/Macwin_bride.git
cd Macwin_bride
brew bundle
make test
make build
make package
```

- `make build` สร้างแอป 3 ตัวและ CLI ที่ `.build/distribution/MacWinBridge/`
- `make package` สร้างแพ็กเกจ `.tar.gz` และ SHA-256 ที่ `.artifacts/`
- Build ทำในโฟลเดอร์แยก ไม่ใช้ Wine และไม่แก้ Steam/prefix/ตัวช่วยของชุดที่กำลังเล่น
- ใน GitHub เปิด **Actions → Build macOS launchers → Run workflow** แล้วดาวน์โหลด artifact จาก run ที่ผ่านได้เช่นกัน

ดูรายละเอียดใน [คู่มือ build](docs/BUILD.md) แพ็กเกจเก็บแอปใน `dist/` และสคริปต์ข้างกัน ให้ย้ายหรือแตกทั้งโฟลเดอร์ `MacWinBridge` ไม่ใช่ย้ายเฉพาะ `.app`

## ใช้งานกับ runtime ที่เตรียมแล้ว

- **Steam Bridge.app** เปิด Steam โดยตรง ตรวจอัปเดตและซ่อมตัวช่วยแสดงผลหลังอัปเดต กด X หน้าต่างหลักแล้วปิด Steam/เกม/Wine ในชุดกลาง; ย่อหน้าต่างได้ตามปกติ บันทึกเกมก่อนปิด
- **MacWin Bridge.app** หน้าจอตรวจสถานะและเลือก World / Iceborne หรือ Rise / Sunbreak ใช้ Steam ชุดเดียวกัน
- **ZZZ Bridge.app** เปิด Zenless Zone Zero ผ่านบัญชี HoYoverse เดิม ใช้ไฟล์เกมที่ติดตั้งใน Steam ต้องปิด Steam ก่อนเปิด ZZZ และออกจาก ZZZ ก่อนกลับไปเปิด Steam ตัวเปิดคืนค่าช่องทาง Steam หลังจบเกม

CLI: `bin/bridge doctor --profile world` หรือ `bin/bridge status --profile rise` จากโฟลเดอร์แพ็กเกจ

## สถานะที่ทดสอบ

ผลจากเครื่องทดสอบ Apple Silicon เท่านั้น ไม่ใช่การรับรองเกมทุกรุ่นหรือทุกเครื่อง:

| โปรแกรม | ผลที่ยืนยัน |
| --- | --- |
| Steam | ล็อกอิน, Library, ดาวน์โหลดเกม และตัวเปิดซ่อม helper หลังไฟล์ถูกแทนที่ |
| Limbus Company | แสดงภาพและเข้าเมนูหลักได้ |
| Monster Hunter: World | เข้าเมนูทั้ง Windowed และ Full Screen หลังปิด Overlay เฉพาะเกม |
| Zenless Zone Zero 3.3 | เข้าเมือง/ฉากเล่นและควบคุมได้ผ่าน HoYoverse ด้วย Wine ชุดกลาง; ทดสอบออกและคืนค่าแล้ว |
| Monster Hunter Rise / Sunbreak | ยังไม่ยืนยันการเล่น |

การทดสอบเกมล่าสุด 3 พฤศจิกายน 2026; CI ตรวจซอร์สและ build แอป ไม่ได้ล็อกอิน Steam หรือรันเกม

## ข้อมูลในเครื่อง

| ตำแหน่ง | เนื้อหา |
| --- | --- |
| `.runtime/` | Wine, DXMT, plugins และ helper ที่เตรียมไว้ในเครื่อง |
| `var/prefixes/shared/` | Windows API environment, registry, เซฟและแคช |
| `var/Steam/` | Steam และคลังเกมเพียงชุดเดียว |
| `var/logs/`, `var/backups/` | Logs และข้อมูลคืนค่าเฉพาะเครื่อง |
| `var/zzz-session.json` | บันทึกคืนค่าหาก ZZZ ถูกขัดจังหวะ; อย่าลบเอง |

โฟลเดอร์เหล่านี้ถูกกันออกจาก Git และแพ็กเกจ build ไม่ควรนำ prefix หรือ logs ที่มีข้อมูลบัญชีขึ้น repository

### บัญชีของผู้ใช้แต่ละคน

การ clone หรือดาวน์โหลดแพ็กเกจ build **ไม่พาข้อมูลล็อกอินของผู้พัฒนาไปด้วย** ผู้ใช้ใหม่ต้องเตรียม Wine/Steam ของตนเองตามคู่มือ runtime แล้วล็อกอิน Steam และ HoYoverse ด้วยบัญชีของตนเอง ข้อมูลที่จำการล็อกอินจะอยู่ในเครื่องนั้นเท่านั้น ตัวเปิดไม่กำหนดชื่อบัญชีหรือรหัสผ่านไว้ในซอร์ส

แจกผ่าน `make package` เท่านั้น อย่าบีบอัดโฟลเดอร์ที่ใช้เล่นทั้งชุด เพราะ `var/` มีบัญชี เซฟ และ registry อยู่ การเพิ่มไฟล์เหล่านี้ใน `.gitignore` ไม่ได้ลบไฟล์ที่เคย commit แล้ว จึงมี `make privacy-check` ตรวจทั้ง Git index และประวัติ ส่วน CI ตรวจอัตโนมัติก่อน build และตัวแพ็กตรวจซ้ำก่อนสร้างไฟล์แจก ตัวตรวจครอบคลุมตำแหน่งข้อมูลส่วนตัวและรูปแบบ credential ที่รู้จัก ไม่ใช่การรับรองว่าไฟล์ใด ๆ จะไม่มีความลับทุกรูปแบบ

## ที่มา

โค้ด Steam webhelper wrapper มาจาก [notpop/steam-on-m1-wine](https://github.com/notpop/steam-on-m1-wine) ตาม [third-party notice](third_party/steam-webhelper/README.md) และ MIT license ที่แนบไว้ ดู [NOTICE.md](NOTICE.md) สำหรับขอบเขตการแจกจ่าย
