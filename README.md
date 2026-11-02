# N4X — Telegram Channel Upload Bot

Apne Telegram channel me seedha **APK, ZIP, PDF, TXT** aur baaki files upload karne
wala bot — phone ki file manager se, description ke saath, bina kisi doosre app ke.

- **Bot name:** N4X
- **Owner:** Hari Jadhav
- **Instagram:** @ur_.krishn._02
- **Telegram:** @nullkrishn

---

## Files

| File | Kaam |
|------|------|
| `null.py` | Main entry point — bot start karta hai (`python3 null.py`) |
| `config.py` | Token, owner details, allowed file types, size limit |
| `database.py` | SQLite — channels, users, upload history |
| `keyboards.py` | Saare messages aur inline buttons |
| `handlers.py` | Connect flow + upload flow + commands |
| `requirements.txt` | Dependency |

---

## Setup (5 steps)

**1. Bot banao**
Telegram me [@BotFather](https://t.me/BotFather) → `/newbot` → naam `N4X` → username
(e.g. `n4x_upload_bot`) → token copy kariye.

**2. Bot ko channel me Admin banao**
Channel → Administrators → Add Admin → apna bot → **Post messages** ✅ ON.
(Yeh step skip kiya to upload fail hoga — Telegram aisa hi kaam karta hai.)

**3. Install**
```bash
cd n4x-bot
python3 -m pip install -r requirements.txt
```

> **Python 3.14 / Termux par:** `python-telegram-bot` **22.8 ya usse naya** chahiye.
> Purani version (21.x) 3.14 par `RuntimeError: There is no current event loop` deti hai.
> Upgrade: `pip install -U "python-telegram-bot>=22.8"`

**4. Token daalo**
```bash
export BOT_TOKEN="123456:ABC-your-token"
```
ya `config.py` me `BOT_TOKEN = "..."` ki jagah seedha paste kar dijiye.

**5. Chalao**
```bash
python3 null.py
```
Terminal me `Bot online: @yourbot` dikhega. Bas.

---

## Bot kaise chalega

**Step 1 — Connect**
`/start` → **Connect Channel** dabaiye:

1. Channel ka **username** — `@mychannel` / `https://t.me/mychannel` / `-100...`
   Bot check karta hai ki wo channel hai aur bot wahan post kar sakta hai ya nahi.
2. Channel ke **owner ka naam**
3. Channel ke **admin ka mobile number** — `+919876543210`

Uske baad bot Telegram se verify karta hai ki aap us channel ke asli **admin** hain,
phir channel DB me save ho jata hai.

**Ek hi line me (sabse fast):**
```
/connect @mychannel Hari Jadhav 9876543210
```
```
/connect @mychannel 9876543210        ← owner naam skip karna ho to
```
Bot us channel me admin hona chahiye, warna yeh bata dega kya karna hai.

**Step 2 — Upload**
```
/apk add
```
→ file bhejiye (APK / ZIP / PDF / TXT) → description likhiye (ya Skip) →
post seedha channel me chala jayega, caption + branding ke saath.

File ke saath hi caption likh denge to description alag se nahi poocha jayega.

---

## Commands

| Command | Kaam |
|---|---|
| `/start` | Main menu |
| `/apk add` | File upload (`/add` aur `/upload` bhi chalte hain) |
| `/connect` | Channel connect (`/connect @channel 9876543210` — ek line me) |
| `/status` | Channel status + bot permission + upload count |
| `/list` | Last 10 uploads |
| `/disconnect` | Channel remove |
| `/about` | Bot + owner details |
| `/cancel` | Current step cancel |
| `/help` | Help |
| `/diag` | Diagnostics — bot ka channel access check |

---

## Ek zaroori baat — mobile number ke baare me

Telegram **Bot API** kisi user ka mobile number verify nahi kar sakta. Bot kisi bhi
number ko "real" prove nahi kar sakta — sirf Telegram khud apne login me OTP bhejta hai.

Isliye is bot me:

- Mobile number **record** ke liye save hota hai (channel ke admin ka contact).
- Asli **security** Telegram ke channel admin rights se aati hai — bot
  `getChatAdministrators` se check karta hai ki upload karne wala banda us channel ka
  admin hai ya nahi. Admin nahi hai to upload block ho jata hai.

Yani number sirf admin ka record hai; galti se bhi koi bahar ka banda aapke channel me
post nahi kar sakta. Yeh design jaan-boojh kar aisa rakha gaya hai — mobile number ko
password ki tarah use karna safe nahi hota, kyunki number guess ya leak ho sakta hai.

## Limits

- File size: **50 MB** tak (Telegram Bot API ki limit). Isse badi file ke liye
  local Bot API server chalana padta hai — tab `config.py` me `MAX_FILE_MB` badha dijiye.
- Allowed types `config.py` ke `ALLOWED_EXTENSIONS` me badle ja sakte hain.
- Ek channel ek waqt me ek hi admin se connected rehta hai.

## Hosting (24×7 chalane ke liye)

Kisi bhi VPS / Railway / Render / Replit par:
```bash
pip install -r requirements.txt
python3 null.py
```
Bot polling mode me chalta hai — koi port ya webhook domain ki zaroorat nahi.
`n4x_bot.db` file ko preserve kariye, usme aapka channel data hai.

---

## Termux (Android) par chalane ke liye

```bash
pkg update && pkg upgrade -y
pkg install python -y
cd ~/h4x                     # jahan bot ki files hain
pip install -U "python-telegram-bot>=22.8"
export BOT_TOKEN="123456:ABC-your-token"
python3 null.py
```

Termux me bot band na ho iske liye `termux-wake-lock` laga lijiye:
```bash
pkg install termux-api -y
termux-wake-lock
```

---

## Troubleshooting

**Connect hi nahi ho raha / bot chup hai**
1. Bot channel me **Admin** hai? → Post messages ✅ (sabse common wajah)
2. **@username** bhejiye — channel ka display name (jaise "My Movies") se channel nahi milta
3. Private channel hai? → us channel ki koi **post bot ko forward** kar dijiye
4. `/diag` bhejiye — bot khud batayega kya gadbad hai

Note: button dabana zaroori nahi — seedha `@mychannel` bhejne par bhi connect shuru ho jata hai.

**`RuntimeError: There is no current event loop in thread 'MainThread'`**
Python 3.14 + purani PTB. Fix:
```bash
pip install -U "python-telegram-bot>=22.8"
```
(`null.py` khud bhi event loop set kar deta hai, par library update karna zaroori hai.)

**`PTBUserWarning: If 'per_message=False' ...`**
Sirf warning hai, bot theek chalega. `null.py` ise off kar deta hai.

**`Member list is inaccessible` (connect ke waqt)**
Bot us channel me admin nahi hai. Channel → Administrators → Add Admin → apna bot
(`@nullkrishn3_bot`) → **Post messages** ✅ → Save. Phir bot me **Retry** dabaiye.

**`Bad Request: chat not found` / upload fail**
Bot channel me admin nahi hai, ya **Post messages** permission off hai.
Channel → Administrators → bot → Post messages ✅. Phir `/status` se check kariye.

**`Forbidden: bot is not a member of the channel chat`**
Bot ko channel se hata diya gaya hai. Dobara admin banao, phir `/status`.

**`Conflict: terminated by other getUpdates request`**
Ek hi token par do jagah bot chal raha hai (jaise Termux + VPS). Ek band kariye.
