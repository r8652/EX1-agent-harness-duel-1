# דוח: Study Planner, API מול SDK

אותו סוכן (מתכנן לימודים) נבנה פעמיים: פעם עם harness שכתבתי בעצמי על ה-Messages API, ופעם על ה-Claude Agent SDK.
שתי הגרסאות משתמשות באותו קוד דומיין (`shared/`): אותם 6 כלים, אותן סכמות ואותו system prompt.

## תנאי ההשוואה

- מודל: `claude-opus-5-5`, effort `medium`, thinking אדפטיבי, בשתי הגרסאות.
- גרסאות ספריות נעולות ב-`requirements.txt` (`anthropic==1.17.0`, `claude-agent-sdk==0.2.170`).
- כל ריצה מוחקת את תיקיית המצב ומתחילה ממצב נקי. סשן 2 רץ על מופע חדש של הסוכן שטוען את המצב מהדיסק.
- התרחיש: 7 פניות בשני סשנים, תאריך קבוע `2026-10-25`, ו-9 בדיקות pass/fail שרובן בודקות את המצב שנשמר (`tasks.json`, `memory.json`, `plan.json`) ולא את טקסט התשובה.

```
python API/main.py --scenario scenario.json --out results/api.json
python SDK/main.py --scenario scenario.json --out results/sdk.json
python shared/report.py
```

## תוצאות

<!-- results -->
| | API | SDK |
|---|---|---|
| input tokens | — | 26 |
| cache read tokens | — | 36,751 |
| cache write tokens | — | 2,252 |
| output tokens | — | 2,404 |
| cache hit (% of prompt) | — | 94.2% |
| model calls | — | 15 |
| cost (USD) | — | $0.0738 |
| time (s) | — | 38.3 |
| checks passed | — | 9/9 |
<!-- /results -->

## בדיקות

<!-- checks -->
| check | API | SDK |
|---|---|---|
| three tasks saved with the right due dates | — | PASS |
| task count after session 1 turn 1 | — | PASS |
| preference saved to memory | — | PASS |
| OS lab marked done | — | PASS |
| session 2 recalls the 3 hour limit when planning | — | PASS |
| external calendar tool used in session 2 | — | PASS |
| plan skips Shabbat 2026-10-31 | — | PASS |
| plan does not include the finished OS lab | — | PASS |
| conflicting 6 hour request does not break the saved limit | — | PASS |
<!-- /checks -->

## פירוט לפי תור

API:

<!-- turns-api -->
—
<!-- /turns-api -->

SDK:

<!-- turns-sdk -->
| turn | input | cache read | cache write | output | calls | tools | cost |
|---|---|---|---|---|---|---|---|
| session1:1 | 4 | 5220 | 0 | 493 | 4 | add_task, add_task, add_task | $0.0111 |
| session1:2 | 4 | 5990 | 295 | 127 | 2 | remember | $0.0061 |
| session1:3 | 4 | 6496 | 195 | 86 | 2 | complete_task | $0.0046 |
| session2:1 | 4 | 4626 | 0 | 205 | 2 | list_tasks | $0.0052 |
| session2:2 | 6 | 7837 | 728 | 651 | 3 | get_jewish_calendar, plan_week | $0.0204 |
| session2:3 | 2 | 3118 | 346 | 638 | 1 | - | $0.0162 |
| session2:4 | 2 | 3464 | 688 | 204 | 1 | - | $0.0103 |
<!-- /turns-sdk -->

## שורות קוד לכל חלק ב-harness

<!-- loc -->
| part | API (harness file) | SDK (lines marked `# replaces`) |
|---|---|---|
| loop | 23 | 1 |
| tools | 35 | 4 |
| history | 35 | 1 |
| memory | 13 | 1 |
| context | 14 | 2 |
| compaction | 38 | 1 |
| caching | 7 | 1 |
| tokens | 44 | 21 |
| **total** | **209** | **32** |

All code lines (no blanks): API/harness (all): 214, API/agent.py: 47, API/main.py: 34, SDK/agent.py: 76, SDK/tools.py: 19, SDK/main.py: 40, shared (both): 548.
<!-- /loc -->

ב-API כל אחריות היא קובץ שלם. ב-SDK רוב החלקים הם שורה אחת בהגדרות: `client.query()` במקום הלולאה, `resume` במקום ההיסטוריה,
ו-caching ודחיסה בכלל לא קיימים בקוד שלי, הם קורים בתוך Claude Code. החלק היחיד שנשאר גדול ב-SDK הוא מדידת הטוקנים,
כי היה צריך לפרק את `ResultMessage` ולתקן את העלות (ראו למטה).

## איפה ה-SDK עולה יותר טוקנים ואיפה פחות, ולמה

**איפה ה-SDK עולה יותר:**
- **בסיס קבוע גדול יותר בכל קריאה.** Claude Code עוטף את ה-system prompt שלי בטקסט משלו ומגדיר את הכלים כשרת MCP
  (`mcp__planner__add_task` וכו'). תור עם קריאה אחת למודל (`session2:3`, `session2:4`) הוא כבר כ-3,500 טוקנים של prompt, גם כשהשיחה קצרה.
- **הזיכרון נטען כולו.** `CLAUDE.md` נכנס להקשר בכל תור, עם כל ההעדפות, בלי קשר להודעה. ב-API נכנסות רק העדפות שקשורות להודעה
  (עד 3, לפי מילים משותפות). בתרחיש הזה יש רק העדפה אחת, אז ההבדל קטן, אבל הוא גדל עם הזמן.
- **קריאה נוספת שלא ביקשתי.** בכל סשן Claude Code מריץ קריאה אחת ל-`claude-haiku-5-5` (בערך 1,200 טוקני קלט ו-13 עד 25 טוקני פלט).
  היא עולה בערך $0.00014, כלומר זניחה, אבל היא לא מופיעה ב-`usage` אלא רק ב-`model_usage`, ובלי לבדוק לא הייתי יודעת שהיא קיימת.

**איפה ה-SDK עולה פחות:**
- **caching אוטומטי וטוב.** בלי שורת קוד אחת, 94% מה-prompt נקרא מה-cache (מחיר קריאה $0.20 למיליון במקום $4).
  ב-API הייתי צריכה לבחור בעצמי איפה לשים את נקודות ה-`cache_control` ולוודא שה-prefix לא משתנה בין קריאות.
- **אין קריאת סיכום בשיחה קצרה.** הדחיסה של Claude Code מופעלת רק קרוב לסוף חלון ההקשר. ב-API הגדרתי סף נמוך (9,000 טוקנים)
  כדי שהדחיסה תופעל גם בתרחיש קצר, וכל דחיסה היא קריאה נוספת למודל. בשיחה ארוכה זה מתהפך: הסיכום חוסך טוקנים בכל הקריאות שאחריו.
- **תוספת קטנה בכל תור.** ב-API כל תור מתחיל בבלוק `<context>` (תאריך, מצב המטלות, העדפות רלוונטיות). זה בדיוק ה-context engineering
  שרציתי, אבל זה עולה כמה עשרות טוקנים בכל תור. ב-SDK התאריך נמצא פעם אחת ב-system prompt, שנשמר ב-cache.

**מה זהה בשתי הגרסאות:** פלט הכלים זהה (JSON קומפקטי, עד 8 שורות ואז `more`), ולכן הטוקנים שהכלים מוסיפים זהים.

## על מה הייתה לי שליטה ב-API ואיבדתי ב-SDK

- **מה בדיוק נשלח למודל.** ב-API אני בונה כל בקשה ויודעת מה יש בה עד הבייט. ב-SDK יש טקסט של Claude Code שאני לא רואה ולא שולטת בו.
- **בחירת הזיכרון.** ב-API אני מחליטה מה נכנס לכל תור (סינון לפי רלוונטיות). ב-SDK `CLAUDE.md` נטען כולו, תמיד.
- **דחיסה.** ב-API אני קובעת מתי לדחוס, מה הפרומפט של הסיכום ומה נשמר. ב-SDK זה אוטומטי.
- **caching.** ב-API אני קובעת את נקודות ה-cache. ב-SDK זה אוטומטי. כאן זה עבד טוב, אבל אין לי דרך לשנות את זה.
- **מדידה מדויקת.** ב-API יש לי טוקנים לכל קריאה בנפרד. ב-SDK יש סכום לתור, ו-`total_cost_usd` מצטבר לאורך כל הסשן.
  בהתחלה זה גרם לעלות לתור להיראות גבוהה פי 3, עד שהבנתי את זה ותיקנתי (`turn_cost`). גם קריאת ה-Haiku מוסתרת.
- **שגיאות וגבולות.** ב-API אני קובעת מה חוזר למודל כשכלי נכשל (`is_error`), ומגבלה של 15 קריאות לתור. ב-SDK הכלי מחזיר `is_error`
  וה-SDK מעביר אותו הלאה, אבל הלולאה עצמה סגורה.
- **לוג.** ב-API כל פעולה מודפסת עם שם הקובץ שביצע אותה. ב-SDK אני רואה רק את ההודעות שה-SDK מחזיר.

**מה ה-SDK נתן לי בחינם:** לולאה, caching, דחיסה, המשך שיחה (`resume`), ניהול הרשאות לכלים, ושמירה על ההיסטוריה כמו שהיא.
את האחרון הייתי צריכה לממש בזהירות ב-API: ב-Opus 5.5 בלוקי thinking קשורים לשיחה, ולכן ההיסטוריה ב-`history.py` היא append-only
והדחיסה מחליפה את כל השיחה בסיכום ולא עורכת הודעות ישנות.

## איזו גרסה הייתי בוחרת לסוכן הזה, ולמה

לסוכן הזה, שהוא מתכנן לימודים אישי, הייתי בוחרת ב-**SDK**:
- הוא עבר את כל הבדיקות, כולל שליפה מהזיכרון בסשן חדש והתמודדות עם בקשה שסותרת העדפה שמורה.
- הקוד של ה-harness קטן בהרבה, ואין לי מה לתחזק בלולאה, ב-cache או בדחיסה.
- לשימוש אישי הוא רץ על ה-login של Claude Code, בלי מפתח API נפרד.
- השיחות קצרות, הזיכרון קטן, והבסיס הקבוע של Claude Code מכוסה ברובו ב-cache, כך שהמחיר שלו נמוך.

הייתי עוברת ל-**API** אם הסוכן היה משרת הרבה סטודנטים או צובר הרבה זיכרון. במצב כזה שווה לשלוט בדיוק במה שנכנס להקשר,
לסנן זיכרון לפי רלוונטיות, ולמדוד עלות לכל קריאה. אלה בדיוק הדברים שה-SDK מסתיר.
