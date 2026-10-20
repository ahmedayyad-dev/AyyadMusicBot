# AyyadMusicBot (DHVbot)

[العربية](#-العربية) ▪ [English](#-english)

---

## ▪ العربية

بوت متطور لبث وتشغيل الموسيقى داخل المكالمات الصوتية للمجموعات والقنوات في تيليجرام، مع التكامل الكامل مع منصة أنغامي عبر [Anghami Music Data and Stream API على RapidAPI](https://rapidapi.com/ahmedyad200/api/anghami-music-data-and-stream).

- **معرف البوت الرسمي على تيليجرام**: [@DHVbot](https://t.me/DHVbot)
- **اشتراك Anghami API**: [RapidAPI - anghami-music-data-and-stream](https://rapidapi.com/ahmedyad200/api/anghami-music-data-and-stream)

---

### المميزات الرئيسية

- **بث عالي الدقة في المكالمات الصوتية**: تشغيل مستقر وفوري داخل المحادثات الصوتية الجماعية بدعم كامل من PyTgCalls.
- **تكامل مباشر مع أنغامي**: إمكانية البحث عن الأغاني بالاسم أو إرسال الروابط المباشرة (`anghami.com/song/...`).
- **التشغيل التلقائي الذكي (Anghami Autoplay)**: استمرار تشغيل مقاطع مقترحة شبيهة تلقائياً بناءً على آخر أغنية تم طلبها عند انتهاء قائمة الانتظار.
- **إدارة متقدمة لقائمة الانتظار**: طابور تشغيل يتسع لـ 50 مقطعاً، مع إمكانية التصفح وإدارة عناصر الانتظار بحرية.
- **واجهة تفاعلية حديثة بدون إيموجي**: رسائل غنية وعصرية (`InputRichMessage`) من Kurigram مع أزرار تحكم تفاعلية (تخطي، إيقاف مؤقت، استئناف، إنهاء) متوافقة مع اتجاه الكتابة من اليمين لليسار.
- **نظام الحسابات المساعدة المتعددة (Multi-Assistant Load Balancing)**: دعم تشغيل عدة حسابات مساعدة (Userbots) في نفس الوقت مع توزيع المجموعات آلياً لتخفيف الحمل.
- **الانضمام الذكي وحماية المشرف (Admin Guard & Mirroring)**: انضمام الحساب المساعد التلقائي للمجموعات عند الحاجة، ونسخ صلاحيات البوت الإشرافية له تلقائياً لضمان إدارة المكالمات.
- **تحميل مباشر وسريع**: تنزيل المقاطع الصوتية في المحادثات الخاصة مع غلاف الألبوم وبيانات المقطع عبر روابط ورموز وصول مؤقتة وآمنة.
- **تعدد اللغات الكامل**: دعم كامل لثلاث لغات تشمل العربية (`ar`) والإنجليزية (`en`) والأوزبكية (`uz`) للمجموعات والخاص.
- **نظام صلاحيات صارم ومرن**:
  - جميع أوامر التشغيل والتحكم في المجموعات مخصصة افتراضياً للمشرفين أصحاب صلاحية **إدارة المحادثات الصوتية** (`can_manage_video_chats`).
  - يمكن للمشرفين من خلال لوحة الإعدادات تعديل نطاق أي أمر ليكون متاحاً **للجميع**.
  - أمر تحديث المشرفين (`تحديث`) متاح **للجميع** لتحديث قائمة المشرفين في أي وقت دون قيود.
  - لوحة الإعدادات (`اعدادات`) مخصصة حصرياً للمشرفين الحاصلين على صلاحية **إدارة المحادثات الصوتية**.
- **التحديث السريع للمطورين**: أمر خاص للمطورين لتحديث البوت مباشرة عبر تيليجرام بسحب التعديلات (`git pull`) وتحديث الحزم (`uv sync`) وإعادة التشغيل التلقائي بدون توقف.
- **أداء فائق مع Redis**: اعتماد كامل على خطوط أنابيب Redis Pipelines لتقليل زمن الاستجابة والتخزين المؤقت لبيانات البحث والتشغيل.

---

### هيكلية المشروع

يلتزم المشروع بهيكل تنظيمي صارم يقتصر على ثلاثة مجلدات رئيسية داخل مجلد العمل:

```
DHVbot/
├── core/               # المنطق الأساسي، المشغل، تكامل أنغامي، الحسابات المساعدة، وقاعدة البيانات
│   ├── anghami.py      # عميل أنغامي والبحث وجلب روابط البث والغلاف
│   ├── config.py       # إعدادات النظام وقراءة المتغيرات البيئية واتصال Redis
│   ├── helper.py       # إدارة الحسابات المساعدة ومكالمات PyTgCalls وموازنة الحمل
│   ├── logger.py       # إعداد وضبط سجلات النظام
│   ├── music.py        # منطق التشغيل والتحميل ومعالجة مسارات الصوت
│   ├── nowplaying.py   # بناء رسائل واجهة التشغيل الحالية والطابور
│   ├── permissions.py  # التحقق من الصلاحيات وإدارة المشرفين وقفل الأوامر
│   ├── player.py       # هيكل بيانات الطابور وحالة التشغيل والتشغيل التلقائي
│   └── pylint_checks.py# فحوصات التحليل الثابت المخصصة لـ Pylint
├── languages/          # ملفات التوطين والترجمة
│   ├── __init__.py     # دوال إدارة واسترجاع النصوص
│   ├── ar.py           # نصوص اللغة العربية
│   ├── en.py           # نصوص اللغة الإنجليزية
│   └── uz.py           # نصوص اللغة الأوزبكية
├── plugins/            # معالجات أحداث تيليجرام
│   ├── bot/            # أوامر البوت الأساسي (الموسيقى، الإعدادات، القوائم، التتبع، التحديث)
│   └── helper/         # أحداث الحسابات المساعدة (حماية الصلاحيات، تتبع المغادرة)
├── .env.example        # نموذج متغيرات البيئة
├── AI_CONSTITUTION.md  # دستور وقواعد العمل البرمجي للمشروع
├── main.py             # نقطة الدخول الرئيسية لتشغيل البوت
├── pyproject.toml      # ملف المشروع والتبعيات لـ uv
└── uv.lock             # قفل إصدارات التبعيات
```

---

### المتطلبات المسبقة

- نظام تشغيل Linux / macOS / Windows
- بايثون 3.12 أو 3.13 (`>=3.12,<=3.13`)
- خادم Redis يعمل على المنفذ الافتراضي `6379`
- أداة إدارة الحزم والبيئات السريعة `uv`
- بيانات اعتماد تطبيق تيليجرام (`API_ID`, `API_HASH`) من my.telegram.org
- رمز توكن بوت تيليجرام من BotFather (للبوت الرسمي: [@DHVbot](https://t.me/DHVbot))
- جلسة نصية (String Session) واحدة أو أكثر لحسابات المساعدين
- مفتاح اشتراك [Anghami Music Data and Stream API على RapidAPI](https://rapidapi.com/ahmedyad200/api/anghami-music-data-and-stream)

---

### خطوات التثبيت والتشغيل

المشروع يعتمد حصرياً على أداة `uv` لإدارة التبعيات وبيئة العمل:

1. **استنساخ المستودع والدخول للمجلد**:
   ```bash
   git clone https://github.com/ahmedayyad-dev/AyyadMusicBot.git
   cd AyyadMusicBot
   ```

2. **تثبيت التبعيات باستخدام uv**:
   ```bash
   uv sync
   ```

3. **إعداد المتغيرات البيئية**:
   قم بإنشاء ملف `.env` بنسخ النموذج:
   ```bash
   cp .env.example .env
   ```
   ثم افتح الملف واملأ البيانات المطلوبة:
   ```env
   API_ID=1234567
   API_HASH=abcdef0123456789abcdef0123456789
   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   HELPER_SESSIONS=string_session_1,string_session_2
   RAPIDAPI_KEY=your_rapidapi_key_here
   DEV_ADMINS=owner:123456789,dev:987654321
   ```

4. **التأكد من تشغيل Redis**:
   ```bash
   redis-cli ping
   # يجب أن يستجيب: PONG
   ```

5. **تشغيل البوت**:
   ```bash
   uv run python main.py
   ```

---

### المتغيرات البيئية

| المتغير | الوصف | مثال / الرابط |
| :--- | :--- | :--- |
| `API_ID` | معرف التطبيق من تيليجرام | `1234567` |
| `API_HASH` | المفتاح السري للتطبيق من تيليجرام | `0123456789abcdef...` |
| `BOT_TOKEN` | رمز التوكن الخاص بالبوت من BotFather | `123456:ABC-DEF...` |
| `HELPER_SESSIONS` | جلسات بايروجرام النصية للحسابات المساعدة (مفصولة بفواصل) | `session1,session2` |
| `RAPIDAPI_KEY` | مفتاح اشتراك أنغامي عبر [RapidAPI Anghami](https://rapidapi.com/ahmedyad200/api/anghami-music-data-and-stream) | `rapidapi_key_here` |
| `DEV_ADMINS` | قائمة مطوري ومشرفي البوت بصيغة `الاسم:المعرف` مفصولة بفواصل | `admin:123456789` |

---

### دليل الأوامر والصلاحيات

#### أوامر المجموعات (Group Commands)

| الأمر بالعربية | الأمر بالإنجليزية | الأمر بالأوزبكية | الصلاحية الافتراضية | الوصف |
| :--- | :--- | :--- | :--- | :--- |
| `تشغيل <الاسم أو الرابط>` | `/play <name or link>` | `ijro <nomi>` | المشرفون (إدارة المكالمات الصوتية) | تشغيل مقطع صوتي في المكالمة أو إضافته للطابور |
| `تحميل <اسم الأغنية>` | `/download <name>` | `yuklash <nomi>` | المشرفون (إدارة المكالمات الصوتية) | البحث عن أغنية وإرسال رابط تحميلها في الخاص |
| `الطابور` | `/queue` | `navbat` | المشرفون (إدارة المكالمات الصوتية) | عرض قائمة الأغاني المنتظرة وحالة التشغيل |
| `تخطي` | `/skip` | `otkaz` | المشرفون (إدارة المكالمات الصوتية) | تخطي الأغنية الحالية والانتقال للتالية |
| `ايقاف` | `/pause` | `pauza` | المشرفون (إدارة المكالمات الصوتية) | إيقاف تشغيل الصوت مؤقتاً |
| `استئناف` | `/resume` | `davom` | المشرفون (إدارة المكالمات الصوتية) | استئناف الصوت الموقوف مؤقتاً |
| `انهاء` | `/stop` أو `/end` | `toxtat` | المشرفون (إدارة المكالمات الصوتية) | إنهاء التشغيل وإفراغ الطابور ومغادرة المكالمة |
| `اعدادات` | `/settings` | `sozlamalar` | المشرفون (إدارة المكالمات الصوتية) | فتح لوحة التحكم بالصلاحيات وإعدادات المجموعة |
| `تحديث` | `/reload` أو `/refresh` | `yangilash` | الجميع (متاح للكل) | تحديث كاش المشرفين في المجموعة |

> **ملاحظة حول الصلاحيات**: يمكن للمشرف صاحب صلاحية إدارة المحادثات الصوتية الدخول إلى لوحة `اعدادات` وتحويل أي أمر من (المشرفين فقط) إلى (للجميع) بضغطة زر واحدة.

#### أوامر المحادثات الخاصة (Private Commands)

| الأمر | الصلاحية | الوصف |
| :--- | :--- | :--- |
| `/start` | الجميع | فتح القائمة الرئيسية واختيار لغة الحساب |
| `/start dl_<token>` | الجميع | استلام الملف الصوتي المحمل بعد طلبه من المجموعة أو الخاص |
| `تحميل <اسم الأغنية>` | الجميع | تحميل وإرسال المقطع الصوتي مباشرة في الخاص |
| `تحديث` أو `تحديث البوت` | مطورو البوت فقط (`DEV_ADMINS`) | تنفيذ `git pull` و `uv sync` وإعادة تشغيل البوت آلياً |

---

### معايير التطوير وجودة الكود

يخضع الكود لقواعد تنظيمية صارمة محددة في ملف [AI_CONSTITUTION.md](AI_CONSTITUTION.md):

- تقييم Pylint بنسبة كاملة `10.00/10` بدون أي أخطاء أو تحذيرات.
- تطبيق فحوصات AST مخصصة في `core/pylint_checks.py`:
  - `R9001` (`redis-pipeline-first`): منع استخدام `asyncio.gather` مع دوال قاعدة البيانات وفرض `pipeline()`.
  - `R9002` (`no-single-use-var`): منع تعريف متغيرات تُستخدم لمرة واحدة فقط ودمجها مباشرة في موقع الاستدعاء.
  - `R9003` (`redis-key-inline`): كتابة مفاتيح Redis مباشرة داخل استدعاءات قاعدة البيانات دون تخزينها في متغيرات وسيطة.
  - `R9004` (`no-function-wrapper`): منع الدوال المغلفة (Wrapper Functions) التي لا تضيف أي منطق برمجي.
- الالتزام بالتحقق الساكن حصرياً بدون تشغيل نسخة البوت أثناء الفحص:
  ```bash
  # فحص ترجمة بايثون الساكنة لجميع الملفات
  uv run python -m py_compile main.py core/*.py plugins/bot/*.py plugins/helper/*.py languages/*.py

  # فحص الجودة والتوافق مع Pylint
  uv run pylint main.py core plugins languages
  ```

---

## ▪ English

A high-performance Telegram music streaming bot for group and channel voice chats, featuring native Anghami platform integration via [Anghami Music Data and Stream API on RapidAPI](https://rapidapi.com/ahmedyad200/api/anghami-music-data-and-stream).

- **Official Telegram Bot**: [@DHVbot](https://t.me/DHVbot)
- **Anghami API Subscription**: [RapidAPI - anghami-music-data-and-stream](https://rapidapi.com/ahmedyad200/api/anghami-music-data-and-stream)

---

### Key Features

- **High-Fidelity Voice Chat Streaming**: Low-latency, uninterrupted audio playback inside group voice chats powered by PyTgCalls.
- **Direct Anghami Integration**: Instant song search by title or direct playback using Anghami song URLs (`anghami.com/song/...`).
- **Smart Autoplay Engine**: Seamlessly discovers and enqueues similar recommended songs from Anghami once the manual queue is exhausted.
- **Advanced Queue Management**: Capacity for up to 50 tracks, with pagination support and real-time status updates.
- **Emoji-Free Modern Rich UI**: Clean, elegant interface built with Kurigram `InputRichMessage` using structural textual symbols and interactive callback buttons (Skip, Pause, Resume, Stop).
- **Multi-Assistant Architecture (Load Balancing)**: Distributes group streaming sessions dynamically across multiple helper userbot accounts (`HELPER_SESSIONS`).
- **Auto Join & Privilege Mirroring**: Helper userbots automatically join groups upon playback requests and mirror the main bot's administrator rights.
- **Private Audio Downloader**: Fast audio delivery in private chat with album covers and metadata, using time-limited download tokens (`dl_<token>`).
- **Tri-Lingual Localization**: Comprehensive localization support for Arabic (`ar`), English (`en`), and Uzbek (`uz`).
- **Granular Group Permissions**:
  - By default, all playback and control commands are restricted to group administrators with **Manage Video Chats** permissions (`can_manage_video_chats`).
  - Administrators can toggle individual command access between **Admins Only** and **Everyone** via the settings panel.
  - The cache refresh command (`/reload`) is open to **everyone** to allow syncing updated admin permissions without restrictions.
  - The settings panel (`/settings`) is strictly accessible only to administrators who have **Manage Video Chats** privileges.
- **Remote Developer Hot-Reload**: Authorized developers (`DEV_ADMINS`) can trigger `git pull`, `uv sync`, and instant process re-execution directly from Telegram.
- **Optimized Redis Caching**: Full use of Redis Pipelines and in-memory caching for minimal latency and maximum throughput.

---

### Architecture Overview

The repository strictly maintains three core directories at the root level:

```
DHVbot/
├── core/               # Core business logic, player queue, Anghami client, helpers, and database
│   ├── anghami.py      # Anghami API client, search, stream resolver, and cover fetcher
│   ├── config.py       # Configuration loader, environment validation, and Redis connection pool
│   ├── helper.py       # Helper accounts coordinator, PyTgCalls call dispatcher, and load balancer
│   ├── logger.py       # Logging formatters and system handlers
│   ├── music.py        # Music orchestration, playback requests, and download handlers
│   ├── nowplaying.py   # Now Playing and Queue rich message builders
│   ├── permissions.py  # Permission verification, admin cache, and command gatekeepers
│   ├── player.py       # In-memory playback state, queue data structure, and autoplay buffer
│   └── pylint_checks.py# Custom AST checkers for Pylint rules
├── languages/          # Localization resources
│   ├── __init__.py     # Language resolver and string formatter
│   ├── ar.py           # Arabic dictionary
│   ├── en.py           # English dictionary
│   └── uz.py           # Uzbek dictionary
├── plugins/            # Telegram event handlers
│   ├── bot/            # Main bot handlers (music commands, settings, private menu, dev updates)
│   └── helper/         # Helper userbot handlers (privilege guard, leave tracker)
├── .env.example        # Environment variables template
├── AI_CONSTITUTION.md  # Repository coding standards and durable rules
├── main.py             # Application entrypoint
├── pyproject.toml      # Project metadata and dependencies managed by uv
└── uv.lock             # Exact dependency lockfile
```

---

### Prerequisites

- Linux, macOS, or Windows
- Python 3.12 or 3.13 (`>=3.12,<=3.13`)
- Redis server running on default port `6379`
- `uv` package and virtualenv manager
- Telegram API credentials (`API_ID`, `API_HASH`) from my.telegram.org
- Telegram Bot Token from BotFather (Official Bot: [@DHVbot](https://t.me/DHVbot))
- One or more Pyrogram string sessions for assistant accounts
- RapidAPI Subscription Key for [Anghami Music Data and Stream API](https://rapidapi.com/ahmedyad200/api/anghami-music-data-and-stream)

---

### Installation & Setup

All operations strictly utilize `uv` for dependency management:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ahmedayyad-dev/AyyadMusicBot.git
   cd AyyadMusicBot
   ```

2. **Sync Dependencies with uv**:
   ```bash
   uv sync
   ```

3. **Configure Environment Variables**:
   Create your `.env` configuration file from the template:
   ```bash
   cp .env.example .env
   ```
   Fill in your actual credentials:
   ```env
   API_ID=1234567
   API_HASH=abcdef0123456789abcdef0123456789
   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   HELPER_SESSIONS=string_session_1,string_session_2
   RAPIDAPI_KEY=your_rapidapi_key_here
   DEV_ADMINS=owner:123456789,dev:987654321
   ```

4. **Verify Redis Connection**:
   ```bash
   redis-cli ping
   # Expected response: PONG
   ```

5. **Run the Bot**:
   ```bash
   uv run python main.py
   ```

---

### Environment Variables

| Variable | Description | Example / Link |
| :--- | :--- | :--- |
| `API_ID` | Telegram API ID from my.telegram.org | `1234567` |
| `API_HASH` | Telegram API Hash from my.telegram.org | `0123456789abcdef...` |
| `BOT_TOKEN` | Telegram Bot Token from BotFather | `123456:ABC-DEF...` |
| `HELPER_SESSIONS` | Comma-separated Pyrogram string sessions for helper userbots | `session1,session2` |
| `RAPIDAPI_KEY` | Subscription key from [RapidAPI Anghami API](https://rapidapi.com/ahmedyad200/api/anghami-music-data-and-stream) | `rapidapi_key_here` |
| `DEV_ADMINS` | Authorized developers in format `name:id,name:id` | `admin:123456789` |

---

### Commands Reference

#### Group Commands

| Arabic Command | English Command | Uzbek Command | Default Scope | Description |
| :--- | :--- | :--- | :--- | :--- |
| `تشغيل <الاسم أو الرابط>` | `/play <name or link>` | `ijro <nomi>` | Admins (Manage Video Chats) | Plays track in voice chat or adds to queue |
| `تحميل <اسم الأغنية>` | `/download <name>` | `yuklash <nomi>` | Admins (Manage Video Chats) | Searches track and provides download link in private |
| `الطابور` | `/queue` | `navbat` | Admins (Manage Video Chats) | Displays upcoming queue and current playback |
| `تخطي` | `/skip` | `otkaz` | Admins (Manage Video Chats) | Skips current track to next in queue |
| `ايقاف` | `/pause` | `pauza` | Admins (Manage Video Chats) | Pauses current audio stream |
| `استئناف` | `/resume` | `davom` | Admins (Manage Video Chats) | Resumes paused audio stream |
| `انهاء` | `/stop` or `/end` | `toxtat` | Admins (Manage Video Chats) | Clears queue and leaves group voice call |
| `اعدادات` | `/settings` | `sozlamalar` | Admins (Manage Video Chats) | Opens group permissions and settings panel |
| `تحديث` | `/reload` or `/refresh` | `yangilash` | Everyone (Unrestricted) | Refreshes cached administrator list |

> **Permissions Note**: Group administrators with voice chat management rights can open `/settings` and toggle any command between `Admins Only` and `Everyone` at any time.

#### Private Chat Commands

| Command | Scope | Description |
| :--- | :--- | :--- |
| `/start` | Everyone | Displays private menu and language selection panel |
| `/start dl_<token>` | Everyone | Delivers requested audio file using download token |
| `تحميل <name>` / `/download <name>` | Everyone | Directly downloads and sends audio track in private chat |
| `تحديث` or `تحديث البوت` | Dev Admins (`DEV_ADMINS`) | Executes `git pull`, `uv sync`, and restarts process |

---

### Code Quality & Standards

This project enforces strict standards documented in [AI_CONSTITUTION.md](AI_CONSTITUTION.md):

- Constant **10.00/10 Pylint score** with zero warnings or violations.
- Custom AST static checkers configured in `core/pylint_checks.py`:
  - `R9001` (`redis-pipeline-first`): Disallows `asyncio.gather` for Redis calls; enforces `pipeline()`.
  - `R9002` (`no-single-use-var`): Prevents redundant variables that are assigned and consumed once.
  - `R9003` (`redis-key-inline`): Mandates inline string formatting for Redis keys directly at database call sites.
  - `R9004` (`no-function-wrapper`): Eliminates unnecessary forwarding wrapper functions.
- Static verification is performed without booting the bot instance:
  ```bash
  # Check python compilation
  uv run python -m py_compile main.py core/*.py plugins/bot/*.py plugins/helper/*.py languages/*.py

  # Run full Pylint suite
  uv run pylint main.py core plugins languages
  ```

---

### License

This project is licensed under the [MIT License](LICENSE).
