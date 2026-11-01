# DayPeek

**Следы за сегодня.** Одна карточка: запуски Windows, пробуждения, падения, USB и установки MSI. Журналы читает сама, другие программы недели не нужны.

**Автор:** darkshade ([@vlx0](https://github.com/vlx0))

**365 дней open source** · **неделя 10 — «Следы»** · день 70.

Не TouchPeek: там файлы в папках. Здесь только сегодня и только журналы System / Application / Kernel-PnP.

---

## Возможности

- одна карточка на сегодня
- запуски (событие 12), пробуждения (Power-Troubleshooter 1), падения (1000/1002), USB (400), MSI (1033–1035)
- без графика, без трея, без журнала Security и без прав администратора

## Установка

```powershell
git clone https://github.com/vlx0/DayPeek.git
cd DayPeek
pythonw run_daypeek.pyw
```

Или `start.bat`.

Нужен Windows 10+ и Python 3.10+. Внешних зависимостей нет.

## Лицензия

MIT. См. [LICENSE](LICENSE).
