# Contributing to ai-router-stack

ขอบคุณที่สนใจ contribute ครับ!

## วิธี contribute

1. Fork repo นี้
2. สร้าง branch ใหม่จาก main
3. ทำการแก้ไข / เพิ่ม feature
4. เขียน test ถ้าเป็นไปได้ (ใน router/tests/)
5. Commit ด้วย conventional commit
6. Push branch แล้วเปิด Pull Request
7. รอ review (ผมจะรีวิวเร็วที่สุด)

## Coding Style

- Python: follow PEP 8 + Black formatter
- Commit message: conventional commits
- Docstring: Google style
- Type hints: ใช้ mypy

## Pull Request Checklist

- [ ] Code passes lint (ruff, black, mypy)
- [ ] Tests pass (ถ้ามี)
- [ ] Update AGENTS.md ถ้ามีการเปลี่ยน architecture
- [ ] ไม่ commit .env หรือ secret

ขอบคุณล่วงหน้าครับ!
