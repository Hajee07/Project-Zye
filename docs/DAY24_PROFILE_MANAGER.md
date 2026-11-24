# Zye AI — Day 24: Persistent Multi-Account Profile Manager

## 1. Profile Discovery & Management

Zye automatically discovers existing profiles installed on Google Chrome by reading `%LOCALAPPDATA%\Google\Chrome\User Data\Local State`.

### Extracted Metadata:
- **`name`**: Display name of the Chrome profile.
- **`user_name`**: Sync email address (if logged in).
- **`gaia_name`**: Google Account profile name.
- **`is_ephemeral`**: Ephemeral profile flag.
- **`avatar_icon`**: Built-in avatar identifier.

---

## 2. Profile Storage and Isolation

To avoid conflicts with host Chrome instances (`SingletonLock`), Zye manages profiles in dedicated directories:
- **Primary Root:** `%LOCALAPPDATA%\ZyeAI\browser_profiles\profile_<profile_id>`
- **Fallback Root:** `<workspace>\data\browser_profiles\profile_<profile_id>`
- **Registry File:** `<root>\registry.json`

---

## 3. Lock Management & Concurrency Protection

`ProfileLockManager` coordinates active sessions:
- Inspects lock files: `lockfile`, `SingletonLock`, `SingletonCookie`, `SingletonSocket`.
- Manages internal `.zye_lock` containing PID and timestamp.
- Automatically cleans stale locks if the process ID is no longer alive in the Windows process table (`psutil`).
- Prevents concurrent process collisions on the same profile directory.

---

## 4. Voice-Friendly Disambiguation Engine (`AccountSelector`)

Supports multilingual resolution across English, Tamil, and Tanglish:

| Query Pattern | Language | Resolved Target |
| :--- | :--- | :--- |
| `work` / `office` | English | Profile tagged `work` |
| `வேலை ஜிமெயில் திற` | Tamil | Profile with Tamil alias `வேலை` |
| `officela search pannu` | Tanglish | Profile with alias `office` |
| `hajee.work@gmail.com` | Email | Exact email match |
| `personal account` | English | Profile tagged `personal` |

If ambiguous or no exact match is found, Zye prompts the user with a bilingual prompt:
```
பல கணக்குகள் உள்ளன: 'Personal Chrome', 'Office Work'. எந்தக் கணக்கைத் திறக்க வேண்டும்?
Multiple accounts found: Personal Chrome, Office Work. Which account would you like to use?
```
