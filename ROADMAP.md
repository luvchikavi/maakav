# מפת דרכים אסטרטגית - מעקב (Maakav)

> מסמך תכנון לשדרוג מערכת מעקב בנייה ממערכת חד-משרדית למערכת Multi-Tenant לשירות 4-5 משרדי שמאות, כ-500 פרויקטים בשנה.
>
> **תאריך:** אפריל 2026
> **גרסה נוכחית:** Phase 9 complete, Phase 10 (Deploy) pending
> **סטאק:** FastAPI + SQLAlchemy async + PostgreSQL | Next.js 15 + TypeScript + Tailwind

---

## תוכן עניינים

1. [מסד נתונים וארכיטקטורה](#1-מסד-נתונים-וארכיטקטורה)
2. [שיפורי ממשק משתמש](#2-שיפורי-ממשק-משתמש)
3. [בקרת גישה והרשאות](#3-בקרת-גישה-והרשאות)
4. [אבטחת מידע](#4-אבטחת-מידע)
5. [ארכיטקטורת Multi-Office](#5-ארכיטקטורת-multi-office)
6. [רגולציה וציות](#6-רגולציה-וציות)
7. [אחסון נתונים וניהול קבצים](#7-אחסון-נתונים-וניהול-קבצים)
8. [ביצועים וסקלביליות](#8-ביצועים-וסקלביליות)
9. [ניטור ו-Observability](#9-ניטור-ו-observability)
10. [פיצ'רים עתידיים (Product Roadmap)](#10-פיצרים-עתידיים-product-roadmap)

---

## 1. מסד נתונים וארכיטקטורה

### מצב נוכחי
- PostgreSQL יחיד על localhost (database: `maakav`)
- 17 מודלים עם `firm_id` filtering בכל query
- Alembic migrations מוגדר אך אין migration chain רציף
- אין גיבויים אוטומטיים
- אין read replicas
- כל הנתונים בסכמה אחת (`public`)

### בעיות
- **אין הפרדת נתונים אמיתית** - סינון `firm_id` ברמת הקוד בלבד, טעות אחת בקוד חושפת נתוני משרד אחר
- **סכנת data leak** - אם מפתח שוכח לסנן לפי `firm_id` ב-query חדש
- **אין גיבוי** - תקלה בדיסק = אובדן כל הנתונים
- **ביצועים** - ככל שמספר הפרויקטים גדל, כל ה-queries סורקים את כל הטבלאות
- **אין high availability** - שרת אחד, אין failover

### המלצות

#### אסטרטגיית Multi-Tenant: Row-Level Security (RLS) - מומלץ

| אפשרות | יתרונות | חסרונות | המלצה |
|---------|---------|---------|-------|
| **Schema-per-tenant** | הפרדה חזקה, migrations פשוטים | Overhead בניהול 5 schemas, connection pooling מורכב | לא מומלץ ל-5 משרדות |
| **Row-Level Security (RLS)** | הפרדה ברמת DB, אין תלות בקוד, שקוף | מורכבות התקנה, overhead קל ב-query | **מומלץ** |
| **מסדי נתונים נפרדים** | הפרדה מושלמת, גיבוי עצמאי | כפל תשתית, עלות גבוהה, אין cross-office queries | Overkill ל-5 משרדות |

**שלבי מימוש RLS:**
1. הוספת PostgreSQL RLS policy לכל טבלה: `CREATE POLICY firm_isolation ON projects USING (firm_id = current_setting('app.current_firm_id')::int)`
2. הגדרת `SET LOCAL app.current_firm_id` בתחילת כל DB session (middleware)
3. שמירת סינון `firm_id` הקיים כ-defense-in-depth
4. בדיקות אוטומטיות שמוודאות שלא ניתן לגשת לנתוני firm אחר

#### Partitioning לביצועים
- **Hash partitioning** על `firm_id` לטבלאות גדולות: `bank_transactions`, `budget_tracking_lines`, `apartments`
- **Range partitioning** על `created_at` ל-`bank_transactions` (partition חודשי/שנתי)
- ב-500 פרויקטים לא צפויה בעיית ביצועים קריטית, אבל כדאי להתכונן

#### גיבויים
- **יומי:** `pg_dump` אוטומטי ל-S3/R2 (cron job)
- **Point-in-Time Recovery:** הפעלת WAL archiving ב-PostgreSQL
- **שבועי:** Full backup עם retention של 30 יום
- **חודשי:** Long-term backup עם retention של שנה
- Railway מציעים automatic backups - לוודא שמופעל

#### Migration Strategy (מצב נוכחי למרובה-משרדות)
1. Freeze נתוני Production
2. הוספת RLS policies (ללא שבירת תאימות)
3. בדיקות מקיפות עם 2 firms בסביבת staging
4. הוספת firm שני ב-production עם ניטור צמוד
5. מעבר הדרגתי של משרדות נוספים

#### Read Replicas
- **שלב 1:** Railway PostgreSQL read replica לדוחות כבדים (report generation, exposure calculations)
- **שלב 2:** AsyncPG connection routing - writes לראשי, reads ל-replica
- **שלב 3:** Dedicated analytics replica עם materialized views לדשבורד

### עדיפות: **P1** (חובה לפני הוספת משרד שני)
### מורכבות: **High** (RLS + migrations + backups = 2-3 שבועות עבודה)

---

## 2. שיפורי ממשק משתמש

### מצב נוכחי
- דשבורד עם 5 KPI cards + טבלת פרויקטים
- 7-step wizard למילוי דוח חודשי
- RTL Hebrew UI עם Tailwind CSS
- Responsive בסיסי (hamburger menu, responsive padding)
- אין offline, אין charts מתקדמים, אין bulk operations
- Next.js 15, React 19, Zustand, TanStack Query

### בעיות
- **אין דשבורד per-office** - כשמוסיפים משרדות, כל אחד צריך לראות רק את הנתונים שלו
- **אין תמיכה ב-offline** - שמאים בשטח צריכים לעבוד בלי חיבור
- **אין data visualization** - אין גרפים, טרנדים, השוואות
- **אין bulk operations** - לא ניתן לעדכן סטטוס ל-10 פרויקטים בבת אחת
- **אין תמיכה בשפות נוספות** - ערבית, אנגלית
- **אין accessibility** - לא עומד ב-WCAG

### המלצות

#### דשבורד per-office
- **Summary dashboard** ברמת firm: סה"כ פרויקטים, ממוצע התקדמות, חשיפה מצטברת
- **Drill-down:** לחיצה על KPI פותחת רשימה מסוננת
- **השוואת פרויקטים:** side-by-side של שני פרויקטים (תקציב, מכירות, חשיפה)
- **Cross-office view (admin בלבד):** סיכום כל המשרדות למנהל המערכת
- **עדיפות: P1** | **מורכבות: Medium**

#### Responsive Design לביקורי שטח
- **Tablet-first layout** לעיזרד הדוח החודשי
- **Touch-optimized:** כפתורים גדולים, swipe בין שלבי הוויזארד
- **צילום:** אינטגרציה עם מצלמת המכשיר ישירות מהדפדפן (`getUserMedia`)
- **GPS tagging:** הוספת מיקום אוטומטי לצילומים
- **עדיפות: P1** | **מורכבות: Medium**

#### PWA - Offline Capability
- **Service Worker** עם Workbox (next-pwa)
- **IndexedDB** לשמירת נתוני ביקור מקומית
- **Background Sync:** סנכרון אוטומטי כש-online חוזר
- **דפים קריטיים ב-offline:** רשימת פרויקטים, שלבי ביקור, upload queue
- **Conflict resolution:** Last-write-wins עם התראה למשתמש
- **עדיפות: P2** | **מורכבות: High**

#### תמיכה בשפות (i18n)
- **Framework:** `next-intl` עם JSON translation files
- **שפות:** עברית (ברירת מחדל), ערבית (RTL), אנגלית (LTR)
- **Dynamic direction:** CSS logical properties (`margin-inline-start` במקום `margin-right`)
- **Number/date formatting:** Intl API עם locale-specific formatting
- **עדיפות: P3** | **מורכבות: Medium**

#### Accessibility (WCAG 2.1 AA)
- **Semantic HTML:** roles, aria-labels, headings hierarchy
- **Keyboard navigation:** Tab order, focus indicators
- **Color contrast:** minimum 4.5:1 ratio
- **Screen reader:** aria-live regions לעדכונים דינמיים
- **RTL:** וידוא שכל ה-focus management עובד ב-RTL
- **עדיפות: P2** | **מורכבות: Medium**

#### Data Visualization
- **Library:** `recharts` (כבר מותקן ב-Climatrix, ניסיון קיים)
- **גרפים מומלצים:**
  - Line chart: התקדמות בנייה vs ניצול תקציב לאורך חודשים
  - Bar chart: מכירות רבעוניות
  - Pie chart: פילוח הוצאות לפי קטגוריה
  - Area chart: חשיפה נטו לאורך זמן
  - Heatmap: מצב פרויקטים (ירוק/צהוב/אדום)
- **עדיפות: P1** | **מורכבות: Low**

#### Bulk Operations
- **Multi-select:** Checkbox בטבלת פרויקטים + toolbar פעולות
- **פעולות:** עדכון סטטוס, הקצאת שמאי, שינוי שלב, יצירת דוח
- **Batch report generation:** יצירת דוחות חודשיים ל-N פרויקטים בלחיצה (task queue)
- **Import/Export:** ייצוא Excel של טבלת פרויקטים עם פילטרים
- **עדיפות: P2** | **מורכבות: Medium**

#### Keyboard Shortcuts
- **Global:** `Ctrl+K` command palette (חיפוש פרויקט, ניווט מהיר)
- **טבלאות:** Arrow keys לניווט, Enter לעריכה, Escape לביטול
- **ויזארד:** `Alt+1..7` לקפיצה לשלב, `Ctrl+Enter` לשמירה
- **Library:** `cmdk` לcommand palette
- **עדיפות: P3** | **מורכבות: Low**

### עדיפות כוללת: **P1-P2** (דשבורד וגרפים P1, PWA ו-a11y P2)
### מורכבות כוללת: **Medium-High**

---

## 3. בקרת גישה והרשאות

### מצב נוכחי
- 3 תפקידים: `admin`, `appraiser`, `viewer`
- כל שמאי רואה את כל הפרויקטים של המשרד
- אין audit trail
- אין session management מתקדם
- אין 2FA
- JWT tokens: access 15 דקות, refresh 7 ימים

### בעיות
- **אין per-project access** - שמאי חדש רואה את כל 100 הפרויקטים, גם כאלה שלא שלו
- **אין granularity** - אין הבדל בין שמאי בכיר למתאמן
- **אין audit trail** - לא ניתן לדעת מי שינה מה ומתי
- **אין 2FA** - סיכון גבוה עם נתונים פיננסיים
- **אין device tracking** - משתמש יכול להיות מחובר מ-10 מכשירים בו-זמנית
- **אין תפקיד לבנק** - בעתיד בנקים ירצו צפייה בדוחות

### המלצות

#### מודל RBAC (Role-Based Access Control) מומלץ

| תפקיד | תיאור | הרשאות |
|--------|-------|--------|
| `system_admin` | מנהל מערכת (אנחנו) | גישה מלאה לכל המשרדות, ניהול tenants |
| `firm_admin` | מנהל משרד שמאות | ניהול משתמשים, כל הפרויקטים, הגדרות משרד |
| `senior_appraiser` | שמאי בכיר | כל הפרויקטים (read), פרויקטים שלו (write), אישור דוחות |
| `appraiser` | שמאי | רק פרויקטים שהוקצו לו, כתיבה מלאה |
| `data_entry` | הזנת נתונים | פרויקטים שהוקצו, רק שלבי data entry (ללא generate) |
| `viewer` | צופה | קריאה בלבד לפרויקטים שהוקצו |
| `bank_contact` | איש קשר בנק | צפייה בדוחות סופיים בלבד, ללא נתוני גלם |

#### מימוש טכני
```
# טבלה חדשה: project_assignments
project_assignments:
  - user_id (FK)
  - project_id (FK)
  - role_override (optional - per-project role)
  - assigned_at, assigned_by

# Permission middleware
@require_permission("project.edit")
@require_project_access(project_id)
async def update_project(...):
```

- **Permission strings:** `project.view`, `project.edit`, `project.delete`, `report.generate`, `report.approve`, `users.manage`, `firm.settings`
- **Role-Permission mapping:** טבלת `role_permissions` ב-DB (ניתן לשינוי בלי deploy)
- **עדיפות: P1** | **מורכבות: High**

#### Per-Project Access
- טבלת `project_assignments` עם user_id + project_id
- Middleware שמוודא assignment לפני כל endpoint שמקבל `project_id`
- `firm_admin` ו-`senior_appraiser` עוקפים (רואים הכל)
- Dashboard מציג רק פרויקטים מוקצים
- **עדיפות: P1** | **מורכבות: Medium**

#### Audit Trail
- **טבלה:** `audit_log` - `user_id`, `action`, `entity_type`, `entity_id`, `old_value` (JSON), `new_value` (JSON), `timestamp`, `ip_address`
- **מימוש:** SQLAlchemy event listener (`after_update`, `after_insert`, `after_delete`)
- **ניקוי:** retention של שנתיים, ארכוב ל-cold storage
- **UI:** דף "היסטוריית שינויים" ב-admin עם פילטרים
- **עדיפות: P1** | **מורכבות: Medium**

#### Session Management
- **Concurrent sessions:** מקסימום 3 מכשירים במקביל per user
- **Device tracking:** טבלת `user_sessions` עם device fingerprint, IP, last_active
- **Force logout:** admin יכול לנתק משתמש מכל המכשירים
- **Session timeout:** 30 דקות inactive = logout אוטומטי
- **עדיפות: P2** | **מורכבות: Medium**

#### Two-Factor Authentication (2FA)
- **שלב 1:** TOTP (Google Authenticator / Microsoft Authenticator) via `pyotp`
- **שלב 2:** SMS OTP (כגיבוי) via Twilio / MessageBird
- **חובה עבור:** `firm_admin`, `system_admin`
- **אופציונלי עבור:** שאר התפקידים (עם המלצה חזקה)
- **Recovery codes:** 10 קודים חד-פעמיים ביצירת 2FA
- **עדיפות: P2** | **מורכבות: Medium**

### עדיפות כוללת: **P1** (RBAC ו-audit trail חובה לפני multi-office)
### מורכבות כוללת: **High**

---

## 4. אבטחת מידע

### מצב נוכחי
- JWT authentication עם access + refresh tokens
- CORS מוגדר לדומיין ספציפי
- `firm_id` filtering בכל query (ברמת הקוד)
- סיסמאות מוצפנות ב-bcrypt
- PostgreSQL על localhost (אין TLS ב-dev)
- קבצים (דוחות, bank statements) בזיכרון / temp files
- אין encryption at rest
- אין API key rotation
- Claude API key ב-environment variable

### בעיות
- **PII חשוף** - שמות רוכשים, תעודות זהות, מספרי חשבון בנק - נשמרים ב-plaintext
- **אין encryption at rest** - גישה לדיסק = גישה לכל הנתונים
- **אין data masking** - viewer רואה את אותם נתונים כמו admin
- **קבצים לא מאובטחים** - bank statements (PDFs) עם מידע פיננסי רגיש
- **API key יחיד** - אין rotation, דליפה = גישה ל-AI API
- **אין penetration testing** - לא ידוע אם יש SQL injection / XSS
- **אין SOC2** - לא רלוונטי כרגע אבל בנקים עלולים לדרוש

### המלצות

#### Encryption at Rest
- **PostgreSQL:** הפעלת `pgcrypto` extension
- **עמודות רגישות:** הצפנת `buyer_name`, `buyer_id_number` עם AES-256
  ```sql
  ALTER TABLE sales_contracts ADD COLUMN buyer_name_encrypted BYTEA;
  -- Application-level encrypt/decrypt with key from vault
  ```
- **Disk-level:** Railway PostgreSQL uses encrypted volumes (לוודא)
- **Backup encryption:** GPG encryption על pg_dump output
- **עדיפות: P1** | **מורכבות: Medium**

#### Encryption in Transit
- **HTTPS:** Vercel + Railway מספקים TLS by default (לוודא HSTS)
- **Database connection:** SSL mode `require` ב-production DATABASE_URL
- **Internal API:** אם יהיו microservices - mTLS
- **Headers:** `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`
- **עדיפות: P1** | **מורכבות: Low**

#### API Key Management
- **Vault:** שימוש ב-Railway secrets / HashiCorp Vault לסודות
- **Rotation policy:** Anthropic API key - rotation כל 90 יום
- **Per-environment keys:** dev/staging/production keys נפרדים
- **Audit:** log כל שימוש ב-API key (cost tracking)
- **עדיפות: P1** | **מורכבות: Low**

#### PII Handling
- **Classification:** מיפוי כל השדות שמכילים PII
  - **רגישות גבוהה:** תעודת זהות, מספר חשבון בנק
  - **רגישות בינונית:** שם רוכש, כתובת
  - **רגישות נמוכה:** שם פרויקט, שם קבלן
- **Tokenization:** תעודות זהות - שמירת hash + 4 ספרות אחרונות בלבד
- **Access control:** PII מלא רק ל-`appraiser` ומעלה
- **Retention:** מחיקת PII אחרי תקופת השמירה הנדרשת
- **עדיפות: P1** | **מורכבות: High**

#### Data Masking
- **Viewer role:** שם רוכש → "א***ב", ת.ז. → "****1234"
- **Bank contact:** רואה רק סיכומים, לא נתוני רוכשים בודדים
- **API-level:** Pydantic response models שונים per role
  ```python
  class SalePublic(BaseModel):  # for viewer
      buyer_name: str  # masked
  class SaleInternal(BaseModel):  # for appraiser
      buyer_name: str  # full
      buyer_id: str    # full
  ```
- **עדיפות: P2** | **מורכבות: Medium**

#### Secure File Storage
- **מעבר ל-S3/R2:** כל ה-uploads (bank statements, guarantees, generated reports)
- **Signed URLs:** pre-signed URLs עם TTL של 15 דקות
- **Bucket policy:** no public access, server-side encryption (SSE-S3)
- **Virus scanning:** ClamAV על uploads (bank statement PDFs)
- **File type validation:** whitelist של MIME types (PDF, XLSX, DOCX)
- **עדיפות: P1** | **מורכבות: Medium**

#### Security Audit
- **SQL Injection:** review כל ה-raw SQL queries (ב-calculate_all, bank parser)
- **XSS:** וידוא sanitization של כל ה-user inputs (שמות פרויקטים, תיאורים)
- **CSRF:** Next.js מטפל, לוודא שה-API דורש Authorization header
- **Rate limiting:** הגבלת login attempts (5 per minute), API calls
- **Dependency audit:** `pip-audit` + `npm audit` ב-CI
- **עדיפות: P1** | **מורכבות: Medium**

#### Penetration Testing
- **המלצה:** pen test חיצוני לפני go-live עם משרד שני
- **Scope:** API endpoints, authentication, file uploads, AI parsing
- **תדירות:** שנתי, או אחרי שינוי משמעותי בארכיטקטורה
- **Budget:** 10,000-30,000 ILS למבדק חיצוני
- **עדיפות: P2** | **מורכבות: Low** (outsource)

#### SOC2
- **לא נדרש כרגע** - אבל אם בנקים ידרשו:
  - Access controls (RBAC + audit trail מכסים)
  - Encryption (at rest + in transit)
  - Monitoring (logging + alerting)
  - Incident response plan
- **אלטרנטיבה:** ISO 27001 (יותר נפוץ בישראל)
- **עדיפות: P3** | **מורכבות: High**

### עדיפות כוללת: **P1** (encryption, PII, file storage)
### מורכבות כוללת: **High**

---

## 5. ארכיטקטורת Multi-Office

### מצב נוכחי
- משרד שמאות אחד (`firm` table עם רשומה אחת)
- כל המשתמשים שייכים לאותו firm
- כל ה-queries מסוננים לפי `firm_id` מה-JWT
- אין הפרדת נתונים ברמת DB
- אין מנגנון onboarding למשרד חדש
- אין billing, אין branding, אין SLA

### בעיות
- **אין tenant isolation אמיתי** - רק application-level filtering
- **אין onboarding flow** - הוספת משרד דורשת עבודה ידנית (seed script)
- **אין הגדרות per-office** - כולם רואים אותו UI
- **אין מודל עסקי** - איך גובים מכל משרד?
- **אין data portability** - משרד שעוזב לא יכול לקחת את הנתונים

### המלצות

#### Tenant Isolation Model
- **RLS + Application filtering** (defense in depth) - ראה סעיף 1
- **Database:** PostgreSQL shared עם RLS policies
- **Middleware:** `set_firm_context` middleware שמגדיר `app.current_firm_id` מה-JWT
- **Testing:** automated tests שמוודאים cross-tenant isolation
- **עדיפות: P1** | **מורכבות: High**

#### Shared Infrastructure vs Dedicated
- **שלב 1 (1-5 משרדות):** Shared infrastructure - DB יחיד, Railway instance יחיד
  - **עלות:** ~$50/month (Railway Pro + PostgreSQL)
  - **יתרון:** פשטות, עלות נמוכה
  - **חיסרון:** noisy neighbor אפשרי
- **שלב 2 (5-20 משרדות):** Shared DB עם connection pooling (PgBouncer)
- **שלב 3 (20+ משרדות):** Dedicated DB per large tenant, shared for small ones
- **עדיפות: P1** | **מורכבות: Low** (שלב 1 כבר קיים כמעט)

#### Onboarding Flow למשרד חדש
1. **Admin creates firm** - שם, לוגו, פרטי קשר
2. **Auto-provision:** יצירת firm_admin user עם סיסמה זמנית
3. **Firm admin setup:** הגדרות משרד, הזמנת משתמשים
4. **Seed data:** קטגוריות תקציב default, milestones default
5. **Welcome wizard:** הדרכה על המערכת
- **עדיפות: P1** | **מורכבות: Medium**

#### Data Ownership & Portability
- **בעלות:** כל firm הוא הבעלים של הנתונים שלו
- **Export:** `GET /firm/export` - ZIP עם JSON/CSV של כל הנתונים
- **Import:** `POST /firm/import` - יבוא מ-export של מערכת אחרת
- **Deletion:** מחיקת firm = מחיקת כל הנתונים (soft delete + 30 ימי grace)
- **עדיפות: P2** | **מורכבות: Medium**

#### Cross-Office Collaboration
- **Shared projects:** פרויקט שמשויך ל-2 משרדות (נדיר, אבל קיים)
- **מימוש:** טבלת `project_firms` (many-to-many) במקום `firm_id` ישיר
- **Permissions:** firm_admin של כל משרד מגדיר הרשאות לצד השני
- **עדיפות: P3** | **מורכבות: High**

#### Per-Office Branding
- **לוגו:** upload בהגדרות firm, מוצג ב-sidebar + דוחות
- **צבעים:** primary color per firm (CSS variables)
- **Report header:** שם המשרד, כתובת, טלפון, לוגו - בכותרת הדוח
- **עדיפות: P2** | **מורכבות: Low**

#### Billing Model
- **המלצה:** subscription per office
  - **Basic:** עד 30 פרויקטים פעילים - 500 ILS/חודש
  - **Professional:** עד 100 פרויקטים - 1,200 ILS/חודש
  - **Enterprise:** unlimited + SLA + custom branding - 2,500 ILS/חודש
- **Payment:** Stripe (כרטיס אשראי) או חשבונית + העברה (מקובל בישראל)
- **Usage tracking:** ספירת פרויקטים פעילים, AI API calls, storage
- **עדיפות: P2** | **מורכבות: Medium**

#### SLA
- **Uptime:** 99.5% (אפשרי עם Railway)
- **Response time:** API < 500ms, דוחות < 30 שניות
- **Support:** email בימי עבודה, תגובה תוך 24 שעות
- **Backup:** RPO 24 שעות, RTO 4 שעות
- **עדיפות: P3** | **מורכבות: Low** (מסמך, לא קוד)

### עדיפות כוללת: **P1** (isolation + onboarding חובה)
### מורכבות כוללת: **High**

---

## 6. רגולציה וציות

### מצב נוכחי
- אין מדיניות שמירת נתונים מוגדרת
- אין מנגנון מחיקה
- אין compliance מוגדר לחוקים ישראליים
- נתונים פיננסיים (דפי בנק, ערבויות) נשמרים ללא הגבלת זמן
- אין תיעוד של מי ניגש לאיזה מידע

### בעיות
- **חוק הגנת הפרטיות (1981)** - חובת רישום מאגר מידע, חובת אבטחה
- **אין data retention policy** - נתונים נשמרים לנצח
- **אין right to deletion** - רוכש לא יכול לבקש מחיקת המידע שלו
- **אין audit לדרישות רגולטוריות** של לשכת שמאי המקרקעין
- **דוחות מעקב** נשלחים לבנקים - חובות נאמנות ודיוק

### המלצות

#### חוק הגנת הפרטיות (תשמ"א-1981)
- **רישום מאגר מידע:** חובה לרשום ברשם מאגרי המידע (רשות הגנת הפרטיות)
  - סוג המידע: פיננסי, נדל"ן, פרטי זיהוי
  - מטרות: ניהול מעקב בנייה, הפקת דוחות לבנקים
  - **פעולה:** הגשת טופס רישום לרשות
- **תקנות אבטחת מידע (2017):** ברמת אבטחה "בינונית" לפחות
  - מינוי ממונה אבטחת מידע
  - נוהלי אבטחה כתובים
  - ביקורת אבטחה שנתית
  - ניהול הרשאות (RBAC מכסה)
  - Audit trail (מכסה)
- **עדיפות: P1** | **מורכבות: Medium** (עבודה משפטית + טכנית)

#### Data Retention Policy

| סוג מידע | תקופת שמירה | הערות |
|-----------|-------------|-------|
| דוחות מעקב (סופיים) | 7 שנים | דרישת רגולציה פיננסית |
| דפי בנק גולמיים | 3 שנים | אחרי סיום פרויקט |
| פרטי רוכשים (PII) | עד 3 שנים אחרי סיום פרויקט | ניתן למחיקה מוקדמת לפי בקשה |
| נתוני תקציב ומעקב | 7 שנים | לצרכי ביקורת |
| Audit logs | 3 שנים | דרישת אבטחת מידע |
| קבצי upload זמניים | 30 יום | cleanup אוטומטי |

- **מימוש:** cron job שמוחק/ארכב לפי policy
- **Archival:** העברה ל-S3 Glacier / R2 Infrequent Access
- **עדיפות: P1** | **מורכבות: Medium**

#### Right to Deletion
- **API:** `POST /privacy/deletion-request` - בקשת מחיקה מרוכש
- **Flow:**
  1. רוכש פונה למשרד השמאות
  2. firm_admin מגיש בקשת מחיקה במערכת
  3. המערכת מסמנת את הנתונים למחיקה
  4. Grace period: 30 יום (במקרה של טעות)
  5. מחיקה בפועל: PII מוחלף ב-anonymized data
- **חריגים:** נתונים הנדרשים לצרכי חוק (דוחות לבנק) - anonymization במקום מחיקה
- **עדיפות: P2** | **מורכבות: Medium**

#### תקנות דיווח פיננסי
- **דוח מעקב בנקאי:** יש לעמוד בפורמט הנדרש ע"י הבנק
- **חתימה דיגיטלית:** שקילת הוספת חתימה דיגיטלית לדוחות (לא נדרש כרגע אך צפוי)
- **אחריות מקצועית:** דוח שמאי הוא מסמך משפטי - versioning + audit trail קריטי
- **אי-שינוי:** דוח שנשלח לבנק לא ניתן לשינוי (immutable) - רק הפקת דוח מתוקן
- **עדיפות: P1** | **מורכבות: Low** (ברובו כבר קיים)

#### שמירת מסמכים למטרות משפטיות
- **Litigation hold:** אפשרות ל-"הקפאת מחיקה" לפרויקט ספציפי
- **Chain of custody:** audit trail מלא למי ניגש לדוח, מתי, מאיפה
- **Export:** יכולת ייצוא כל המסמכים של פרויקט ב-ZIP (לצרכי משפט/ביקורת)
- **עדיפות: P3** | **מורכבות: Low**

#### תאימות לדרישות לשכת שמאי המקרקעין
- **קוד אתי:** וידוא שהמערכת מאפשרת עמידה בכללי האתיקה
- **ביקורת עמיתים:** אפשרות ל-senior_appraiser לבקר ולאשר דוח
- **תיעוד:** שמירת כל גרסאות הדוח (draft → review → approved → sent)
- **עדיפות: P2** | **מורכבות: Low**

### עדיפות כוללת: **P1** (רישום מאגר + retention policy חובה)
### מורכבות כוללת: **Medium**

---

## 7. אחסון נתונים וניהול קבצים

### מצב נוכחי
- דוחות Word נוצרים כ-StreamingResponse (לא נשמרים)
- Bank statement PDFs נקראים ב-AI ונזרקים (רק ה-transactions נשמרים)
- Guarantee Excel/PDF - נקראים ונזרקים
- אין file storage service
- אין versioning
- אין CDN

### בעיות
- **אין שמירת קבצים מקור** - דף בנק שהועלה לא ניתן לצפייה חוזרת
- **אין היסטוריית דוחות** - דוח שנוצר ולא הורד אבד
- **אין file versioning** - אם מעלים guarantee חדש, הישן נמחק
- **אין backup של קבצים** - רק DB מגובה (בעתיד)
- **Performance** - יצירת דוח Word + PDF היא פעולה כבדה, אין caching

### המלצות

#### File Storage Strategy
- **Provider:** Cloudflare R2 (S3-compatible, חינמי egress, DataCenter באירופה)
- **Alternative:** AWS S3 (אם צריך region ספציפי)
- **Bucket structure:**
  ```
  maakav-files/
  ├── {firm_id}/
  │   ├── uploads/           # Bank statements, guarantees, Excel files
  │   │   ├── {project_id}/
  │   │   │   ├── bank-statements/
  │   │   │   ├── guarantees/
  │   │   │   └── budgets/
  │   ├── reports/           # Generated reports (Word + PDF)
  │   │   ├── {project_id}/
  │   │   │   ├── report-001-2026-03.docx
  │   │   │   ├── report-001-2026-03.pdf
  │   │   │   └── report-002-2026-04.docx
  │   └── branding/          # Firm logos, templates
  ```
- **עדיפות: P1** | **מורכבות: Medium**

#### File Versioning
- **R2/S3 versioning:** הפעלת object versioning ב-bucket
- **Application-level:** טבלת `file_versions` עם `version_number`, `s3_key`, `uploaded_by`, `created_at`
- **UI:** "היסטוריית גרסאות" - לחיצה מציגה כל הגרסאות עם אפשרות להוריד
- **עדיפות: P2** | **מורכבות: Low**

#### Storage Cost Optimization
- **Lifecycle rules:**
  - Uploads ישנים מ-6 חודשים → Infrequent Access
  - Uploads ישנים מ-2 שנים → Archive (Glacier/R2 IA)
  - Temp files → מחיקה אחרי 30 יום
- **Compression:** gzip על JSON exports, דוחות Word כבר compressed
- **Deduplication:** hash-based dedup ל-uploads זהים
- **Budget estimate:**
  - 5 משרדות x 100 פרויקטים x ~10 files x ~5MB = ~25GB/year
  - R2: ~$0.375/month (0.015/GB) - זניח
- **עדיפות: P3** | **מורכבות: Low**

#### CDN for Reports
- **Cloudflare CDN** (חינם עם R2) לדוחות שנוצרו
- **Cache policy:** reports are immutable - cache forever
- **Signed URLs:** TTL 15 דקות, per-user, per-file
- **עדיפות: P2** | **מורכבות: Low**

#### Database Maintenance
- **Auto-vacuum:** וידוא שמוגדר ב-PostgreSQL (Railway default)
- **REINDEX:** שבועי על indexes של טבלאות גדולות
- **ANALYZE:** אחרי bulk imports (apartments, bank transactions)
- **Connection pooling:** PgBouncer ב-production (Railway add-on)
- **Monitoring:** `pg_stat_statements` לזיהוי slow queries
- **עדיפות: P2** | **מורכבות: Low**

#### Archival Strategy
- **פרויקט "שלם":** סטטוס "archived" אחרי טופס 4 + דוח סופי
- **Archived projects:**
  - Read-only ב-UI (אפשר צפייה, אי אפשר עריכה)
  - DB: סימון `is_archived=True`, excluded from dashboard calculations
  - Files: העברה ל-cold storage אחרי 6 חודשים
- **Restore:** admin יכול לשחזר פרויקט ארכיוני (rare)
- **עדיפות: P2** | **מורכבות: Low**

### עדיפות כוללת: **P1** (file storage) / **P2** (versioning, maintenance)
### מורכבות כוללת: **Medium**

---

## 8. ביצועים וסקלביליות

### מצב נוכחי
- Backend: FastAPI async, single instance (Railway)
- DB: PostgreSQL shared, no read replicas
- אין caching layer
- אין task queue (כל הפעולות סינכרוניות)
- דוח Word נוצר on-request (~3-5 שניות)
- AI bank parsing: ~10-30 שניות per PDF
- אין CDN לstatic assets (Vercel מספק)
- ~70 API endpoints, ~17,500 LOC

### בעיות
- **Report generation blocks request** - משתמש ממתין 5+ שניות לדוח
- **AI parsing blocks request** - 30 שניות לdif בנק, timeout אפשרי
- **אין caching** - dashboard calculations run every page load
- **500 פרויקטים** - ה-queries הנוכחיים לא optimized לScale
- **Connection limits** - Railway PostgreSQL מוגבל ב-connections

### המלצות

#### Bottleneck Analysis
- **Report generation (3-5 sec):** CPU-bound, blocks worker
- **AI bank statement parsing (10-30 sec):** IO-bound, API call to Anthropic
- **Calculations endpoint (1-2 sec):** multiple DB queries, recalculates every time
- **Dashboard (500ms):** aggregation queries across all projects
- **Excel upload + parse (2-5 sec):** IO-bound, pandas processing

#### Caching Strategy (Redis)
- **Provider:** Railway Redis add-on (~$5/month) / Upstash Redis (serverless)
- **Cache targets:**
  - Dashboard KPIs: TTL 5 דקות (invalidate on project update)
  - Calculations results: TTL 1 שעה (invalidate on monthly report change)
  - User permissions: TTL 15 דקות
  - Apartment lists: TTL 1 שעה
- **Implementation:** `fastapi-cache2` עם Redis backend
- **Cache invalidation:** event-driven - כל update מוחק את ה-cache הרלוונטי
- **עדיפות: P2** | **מורכבות: Medium**

#### Task Queue (arq + Redis)
- **כבר בשימוש ב-Climatrix** - ניסיון קיים עם arq
- **Tasks לqueue:**
  - Report generation (Word + PDF) → return job_id, poll for completion
  - Bank statement AI parsing → upload → return job_id → poll
  - Batch report generation (multiple projects)
  - Excel imports (apartments, budgets)
  - Data export (full firm export)
- **Worker:** dedicated Railway service (`python -m app.worker`)
- **UI:** progress indicator / "הדוח מוכן להורדה" notification
- **עדיפות: P1** | **מורכבות: Medium**

#### Connection Pooling
- **PgBouncer:** Railway PostgreSQL add-on
- **Settings:** max 20 connections per worker, transaction mode
- **SQLAlchemy:** `pool_size=10, max_overflow=20, pool_recycle=300`
- **Monitoring:** connection count alerts
- **עדיפות: P1** | **מורכבות: Low**

#### Query Optimization
- **Indexes:** composite indexes על (`firm_id`, `project_id`), (`monthly_report_id`, `category`)
- **N+1 prevention:** `selectinload` / `joinedload` על relationships
- **Pagination:** cursor-based pagination על טבלאות גדולות
- **Materialized views:** dashboard summary view, refreshed on schedule
- **EXPLAIN ANALYZE:** audit כל ה-queries שלוקחים >100ms
- **עדיפות: P2** | **מורכבות: Medium**

#### Load Testing
- **Tool:** `locust` (Python, easy setup)
- **Scenarios:**
  - 50 concurrent users, normal browsing (dashboard, project views)
  - 10 concurrent report generations
  - 5 concurrent bank statement uploads
  - Peak: 100 users during monthly report period
- **Target:** P95 < 1 second, P99 < 3 seconds
- **Schedule:** לפני כל major release
- **עדיפות: P2** | **מורכבות: Low**

#### Horizontal Scaling
- **שלב 1 (נוכחי):** Single instance, vertical scaling (more RAM/CPU on Railway)
- **שלב 2 (10+ משרדות):** 2 web workers + 1 task worker
- **שלב 3 (20+ משרדות):** Auto-scaling web workers, dedicated DB
- **Stateless:** הקוד כבר stateless (JWT, no server-side sessions) - ready to scale
- **עדיפות: P3** | **מורכבות: Medium**

### עדיפות כוללת: **P1** (task queue + connection pooling) / **P2** (caching, optimization)
### מורכבות כוללת: **Medium**

---

## 9. ניטור ו-Observability

### מצב נוכחי
- Health check endpoint: `GET /health`
- Basic Python logging (print/logger)
- אין error tracking
- אין performance monitoring
- אין usage analytics
- אין alerting
- אין cost tracking של AI API

### בעיות
- **שגיאות נעלמות** - אין notification כש-endpoint נכשל
- **אין visibility** - לא ידוע כמה זמן לוקח כל request
- **אין cost control** - שימוש ב-Claude API ללא מעקב
- **אין capacity planning** - לא ידוע כמה resources צורכים
- **אין user analytics** - לא ידוע אילו features בשימוש

### המלצות

#### Structured Logging
- **Library:** `structlog` (Python) - JSON structured logs
- **Fields:** timestamp, level, request_id, user_id, firm_id, endpoint, duration
- **Log levels:** ERROR (alerts), WARNING (monitoring), INFO (audit), DEBUG (dev only)
- **Output:** JSON ל-Railway logs → drain ל-Datadog/Logflare
- **Frontend:** `next-logger` / custom error boundary with reporting
- **עדיפות: P1** | **מורכבות: Low**

#### Error Tracking
- **Provider:** Sentry (חינם עד 5,000 events/month)
- **Backend:** `sentry-sdk[fastapi]` - auto-capture exceptions
- **Frontend:** `@sentry/nextjs` - React error boundaries + API errors
- **Config:** environment tagging, user context, breadcrumbs
- **Alerts:** Slack/email notification על כל error חדש
- **עדיפות: P1** | **מורכבות: Low**

#### Performance Monitoring
- **Sentry Performance** (כלול ב-Sentry)
  - Transaction tracing: כל request מ-frontend → backend → DB
  - Slow query detection
  - Web Vitals (LCP, FID, CLS) ב-frontend
- **Custom metrics:**
  - Report generation time
  - AI parsing time + success rate
  - DB query count per request
- **עדיפות: P1** | **מורכבות: Low**

#### Health Checks & Alerting
- **Health endpoint:** extend `/health` to check DB, Redis, S3 connectivity
- **Uptime monitoring:** Railway built-in / UptimeRobot (חינם)
- **Alerts:**
  - Downtime > 1 minute → SMS + Slack
  - Error rate > 5% → Slack
  - Response time P95 > 3 sec → Slack
  - DB connections > 80% → Slack
  - Disk usage > 80% → Email
- **עדיפות: P1** | **מורכבות: Low**

#### Usage Analytics per Office
- **טבלה:** `usage_stats` - firm_id, metric, value, date
- **Metrics:**
  - פרויקטים פעילים
  - דוחות שנוצרו החודש
  - AI API calls (bank parsing, classification)
  - Storage used
  - Active users
- **Dashboard:** admin panel עם usage per firm
- **עדיפות: P2** | **מורכבות: Medium**

#### AI API Cost Tracking
- **Log כל קריאה:** model, tokens_in, tokens_out, cost, purpose
- **Monthly report:** סה"כ עלות AI per firm
- **Budget alerts:** התראה כשfirm חורגת מ-budget
- **Optimization:** cache AI results עבור patterns חוזרים
- **Cost estimate:**
  - Bank statement parsing: ~$0.05-0.15 per page (Claude Sonnet)
  - Transaction classification: ~$0.01 per batch (Claude Haiku)
  - 5 משרדות x 100 פרויקטים x 12 חודשים x $0.10 = ~$600/year
- **עדיפות: P2** | **מורכבות: Low**

### עדיפות כוללת: **P1** (logging + Sentry + health checks)
### מורכבות כוללת: **Low-Medium**

---

## 10. פיצ'רים עתידיים (Product Roadmap)

### מצב נוכחי
- מערכת עובדת end-to-end: הזנת נתונים → חישובים → דוח Word/PDF
- 7-step wizard, 9 calculator services, 11 פרקי דוח
- AI: bank statement parsing + transaction classification
- דשבורד עם 5 KPIs
- ניהול משתמשים בסיסי

### פיצ'רים מוצעים

#### 10.1 אפליקציית מובייל לביקורי שטח
**מצב נוכחי:** שמאים מצלמים בטלפון, שולחים ב-WhatsApp, מעתיקים ידנית למערכת
**בעיות:** תהליך ידני, תמונות הולכות לאיבוד, אין קשר למערכת
**המלצות:**
- **PWA (שלב 1):** גרסת web מותאמת עם camera access + offline queue
- **Native app (שלב 2):** React Native / Expo עם:
  - צילום עם GPS tagging אוטומטי
  - סימון אחוז התקדמות בנייה (slider) עם צילום ראיה
  - Upload queue שמסתנכרן כש-online
  - Push notifications (דוח מוכן, שינוי בפרויקט)
- **עדיפות: P1** | **מורכבות: High**

#### 10.2 התראות WhatsApp/SMS
**מצב נוכחי:** אין התראות, הכל ידני
**בעיות:** בנקים מחכים לדוחות, שמאים שוכחים מועדים
**המלצות:**
- **WhatsApp Business API:** התראה אוטומטית לבנק כשדוח מוכן
- **SMS (Twilio):** תזכורת לשמאי 3 ימים לפני deadline
- **Email:** סיכום שבועי למנהל משרד
- **Notification center:** ב-UI עם bell icon + badge
- **Templates:**
  - "דוח מעקב #{number} לפרויקט {name} מוכן להורדה"
  - "תזכורת: דוח חודשי לפרויקט {name} טרם הוגש"
  - "התראה: חריגת תקציב בפרויקט {name} ({percent}%)"
- **עדיפות: P1** | **מורכבות: Medium**

#### 10.3 אינטגרציית בנקים (API)
**מצב נוכחי:** שמאי מוריד PDF מהבנק ומעלה למערכת
**בעיות:** ידני, מועד לטעויות, עיכובים
**המלצות:**
- **Open Banking Israel:** כשיהיה זמין (PSD2-equivalent) - שליפה אוטומטית
- **שלב ביניים:** API לבנקים שמציעים (הפועלים, לאומי יש API לעסקים)
- **Fallback:** המשך upload ידני עם AI parsing
- **עדיפות: P3** | **מורכבות: High** (תלוי בבנקים)

#### 10.4 עדכון מדדים אוטומטי (מדד תשומות הבנייה)
**מצב נוכחי:** שמאי מזין ידנית את מדד תשומות הבנייה מאתר הלמ"ס
**בעיות:** שכחה, הזנה שגויה, עיכוב בפרסום מדד
**המלצות:**
- **CBS API:** הלמ"ס מפרסמת מדדים ב-API (data.gov.il)
- **Auto-fetch:** cron job חודשי שמושך את המדד העדכני
- **Notification:** התראה כשמדד חדש התפרסם
- **Validation:** השוואה לערך שהוזן ידנית (אם קיים)
- **URL:** `https://apis.cbs.gov.il/series/data/list?id=120010&format=json`
- **עדיפות: P2** | **מורכבות: Low**

#### 10.5 Marketplace תבניות דוחות
**מצב נוכחי:** תבנית דוח אחת לכל הבנקים
**בעיות:** כל בנק רוצה פורמט מעט שונה
**המלצות:**
- **Template engine:** Jinja2-based templates לפרקי דוח
- **Per-bank templates:** הפועלים, לאומי, דיסקונט, מזרחי - כל אחד עם הTemplate שלו
- **Custom fields:** firm_admin יכול להוסיף/להסיר פרקים
- **Import/Export:** templates ניתנים לשיתוף בין משרדות
- **עדיפות: P2** | **מורכבות: Medium**

#### 10.6 פורטל לקוחות (יזם/קבלן)
**מצב נוכחי:** יזם מקבל דוח ב-email
**בעיות:** אין שקיפות, יזם לא יכול לעקוב בזמן אמת
**המלצות:**
- **Read-only portal:** כניסה עם קוד חד-פעמי
- **תצוגה:** סטטוס פרויקט, אחוז בנייה, מכירות, התראות
- **Downloads:** דוחות שאושרו להפצה
- **Branding:** לוגו המשרד השמאי
- **עדיפות: P3** | **מורכבות: Medium**

#### 10.7 אינטגרציה עם מערכות ממשלתיות
**מצב נוכחי:** אין אינטגרציה
**בעיות:** שמאי בודק ידנית ברשם החברות, רשות המסים
**המלצות:**
- **רשם החברות:** שליפת פרטי יזם/קבלן (API זמין)
- **רשות המסים:** אימות תעודת עוסק מורשה (API זמין)
- **טאבו:** בדיקת רישום קרקע (API מוגבל)
- **רשות ניירות ערך:** מידע על יזמים ציבוריים (API MAYA)
- **עדיפות: P3** | **מורכבות: Medium**

### עדיפות כוללת: **P1** (mobile + notifications) / **P2-P3** (אינטגרציות)
### מורכבות כוללת: **Medium-High**

---

## סיכום עדיפויות

### P1 - חובה לפני Multi-Office Launch

| # | נושא | מורכבות | הערכת זמן |
|---|------|---------|-----------|
| 1 | RLS + tenant isolation | High | 2 שבועות |
| 2 | RBAC + per-project access | High | 2 שבועות |
| 3 | Audit trail | Medium | 1 שבוע |
| 4 | File storage (S3/R2) | Medium | 1 שבוע |
| 5 | Encryption (PII, transit) | Medium | 1 שבוע |
| 6 | Onboarding flow למשרד | Medium | 1 שבוע |
| 7 | Task queue (report gen, AI) | Medium | 1 שבוע |
| 8 | Sentry + structured logging | Low | 2-3 ימים |
| 9 | Backup strategy | Low | 1 יום |
| 10 | רישום מאגר מידע | Medium | 1 שבוע (משפטי) |
| 11 | Dashboard per office + charts | Medium | 1 שבוע |
| 12 | Connection pooling | Low | 1 יום |
| **סה"כ P1** | | | **~10-12 שבועות** |

### P2 - שיפורים חשובים (3-6 חודשים אחרי launch)

| # | נושא | מורכבות | הערכת זמן |
|---|------|---------|-----------|
| 1 | PWA offline capability | High | 2 שבועות |
| 2 | WhatsApp/SMS notifications | Medium | 1 שבוע |
| 3 | Redis caching | Medium | 1 שבוע |
| 4 | Data masking per role | Medium | 1 שבוע |
| 5 | 2FA authentication | Medium | 1 שבוע |
| 6 | Per-office branding | Low | 3 ימים |
| 7 | Billing model (Stripe) | Medium | 1 שבוע |
| 8 | Bulk operations | Medium | 1 שבוע |
| 9 | Accessibility (WCAG) | Medium | 2 שבועות |
| 10 | Auto index updates (CBS) | Low | 2 ימים |
| 11 | Data retention automation | Medium | 1 שבוע |
| 12 | Report templates per bank | Medium | 1 שבוע |
| **סה"כ P2** | | | **~12-14 שבועות** |

### P3 - Nice to Have (6-12 חודשים)

| # | נושא | מורכבות |
|---|------|---------|
| 1 | i18n (Hebrew/Arabic/English) | Medium |
| 2 | Bank API integration | High |
| 3 | Client portal (developer view) | Medium |
| 4 | Government integrations | Medium |
| 5 | Cross-office collaboration | High |
| 6 | SOC2/ISO 27001 | High |
| 7 | Native mobile app | High |
| 8 | Horizontal scaling | Medium |
| 9 | Keyboard shortcuts | Low |
| 10 | Penetration testing | Low (outsource) |

---

## סדר ביצוע מומלץ

```
שלב א' (חודשים 1-3): תשתית Multi-Tenant
├── RLS policies
├── RBAC + project assignments
├── Audit trail
├── S3 file storage
├── Sentry + logging
├── Backups
└── Deploy to production (single office)

שלב ב' (חודשים 3-5): Onboarding + Security
├── Firm onboarding flow
├── PII encryption
├── Task queue (arq + Redis)
├── Dashboard improvements + charts
├── Connection pooling
└── Onboard office #2

שלב ג' (חודשים 5-8): Scale + Polish
├── PWA / mobile
├── WhatsApp notifications
├── Redis caching
├── 2FA
├── Per-office branding
├── Billing
└── Onboard offices #3-5

שלב ד' (חודשים 8-12): Advanced Features
├── Accessibility
├── Bulk operations
├── Report templates per bank
├── Auto CBS index
├── Data retention automation
└── Client portal
```

---

> **הערה:** מסמך זה הוא תכנוני בלבד. אין בו קוד או שינויים במערכת. יש לעדכן את המסמך לאחר כל שלב שמושלם.
>
> **נכתב:** אפריל 2026
> **עודכן לאחרונה:** אפריל 2026
