# EX1 - Agent Harness Duel

סוכן אחד, שני harnesses: אותו סוכן נבנה פעמיים - פעם על ה-Messages API (harness שכתבתי בעצמי) ופעם על ה-Claude Agent SDK.

## הסוכן: Study Planner - מתכנן לימודים

סוכן שעוזר לסטודנטית לנהל את המטלות של הסמסטר: רישום מטלות ומועדי הגשה, סימון מה הושלם,
ובניית תוכנית עבודה שבועית שמתחשבת בשבתות ובחגים (לא מתכננים עבודה בשבת ובחג).

### 1. Tools

| כלי | סוג | מה הוא עושה |
|-----|-----|-------------|
| `add_task` | מקומי (קובץ JSON) | הוספת מטלה: קורס, כותרת, תאריך הגשה, הערכת שעות |
| `list_tasks` | מקומי | רשימת מטלות, עם סינון לפי קורס / טווח ימים / סטטוס |
| `complete_task` | מקומי | סימון מטלה כהושלמה |
| `plan_week` | מקומי | בניית תוכנית עבודה לשבוע לפי מועדי הגשה וימים חסומים |
| `get_jewish_calendar` | **חיצוני** - Hebcal API | שבתות וחגים בטווח תאריכים (`hebcal.com`, ללא מפתח) |

### 2. Memory

הסוכן זוכר בין סשנים:
- **המטלות עצמן** - נשמרות בקובץ `tasks.json` (מצב).
- **העדפות והחלטות** - כלי `remember` ששומר עובדות כמו "אני לומדת רק בבוקר", "מקסימום 4 שעות ביום",
  "החלטנו לדחות את מטלה 3 בקורס אלגוריתמים". נשמרות בקובץ זיכרון על הדיסק.
- **היסטוריית השיחה** - נשמרת לדיסק (append-only) ומאפשרת להמשיך שיחה.

בסשן חדש הסוכן טוען את הזיכרון מהדיסק ומשתמש בו בלי שהמשתמשת תחזור על עצמה.

### 3. Context engineering

הסוכן לא מקבל בכל תור את כל המידע:
- רק העדפות הזיכרון **שרלוונטיות להודעה הנוכחית** נכנסות להקשר (התאמה לפי מילות מפתח ותגיות).
- המטלות לא נשפכות ל-prompt - הסוכן שולף אותן דרך `list_tasks` עם סינון, רק כשצריך.
- תאריך היום וסיכום קצר של המצב (כמה מטלות פתוחות, הקרובה ביותר) נכנסים בשורה אחת.
- כשהשיחה מתארכת - דחיסה (compaction) של תורות ישנים לסיכום.

### 4. Token optimization

- פלט כלים קומפקטי: JSON בלי רווחים, רק השדות הנחוצים, קיצור רשימות ארוכות ("ועוד 12 מטלות").
- תיאורי כלים וסכמות קצרים.
- prompt caching על ה-system prompt וההגדרות של הכלים.
- מדידה לכל תור: input, cache read, cache write, output, מספר קריאות למודל, עלות וזמן.

## מבנה

```
study-planner-tamar/
  shared/        כלים ונתונים משותפים (planner, calendar_api, store, tool_specs, runner)
  API/           main.py  agent.py  harness/{loop,tools,history,memory,context,compaction,caching,tokens}.py
  SDK/           main.py  agent.py  tools.py
  tests/         בדיקות offline עם client מדומה, בלי מפתח ובלי רשת
  scenario.json  התרחיש
  results/       api.json  sdk.json
  REPORT.md
```

## הרצה

```
pip install -r study-planner-tamar/requirements.txt
cd study-planner-tamar
python -m unittest discover -s tests
python API/main.py --scenario scenario.json --out results/api.json
python SDK/main.py --scenario scenario.json --out results/sdk.json
python shared/report.py
```

גרסת ה-API צריכה `ANTHROPIC_API_KEY` כמשתנה סביבה בטרמינל, לעולם לא בקוד ולא בגיט. גרסת ה-SDK רצה על ה-login של Claude Code,
ומוחקת את `ANTHROPIC_API_KEY` מהסביבה לפני שהיא מפעילה את Claude Code, כדי שהחיוב לא יעבור למפתח גם אם הוא מוגדר באותו טרמינל.
בלי `--scenario` שתי הגרסאות נפתחות לשיחה רגילה.
