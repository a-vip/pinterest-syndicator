# Pinterest Visual Syndicator & Traffic Engine

Autonomous visual syndication engine and evergreen search funnel for **[aviperera.com](https://aviperera.com)**.

Every 12 hours, this engine discovers new essays, dossiers, and research published on `aviperera.com`, extracts the high-resolution featured image or autonomously synthesizes a branded editorial 1000×1500 card, and publishes it to Pinterest via the Pinterest API v5.

---

## 🚀 Key Features

1. **Pinterest API v5 Native**:
   - Publishes directly to your designated Pinterest board using official v5 endpoints (`/v5/pins`).
   - Automatically formats character boundaries (<100 characters for pin titles, <500 characters for rich descriptions with relevant hashtags).
2. **Autonomous Visual Card Generation**:
   - Solves internet image reuse & copyright concerns by dynamically generating beautiful dark-mode 1000×1500 (2:3 aspect ratio) editorial SVG cards in `generated_cards/`.
   - Embeds title typography, categorical badges, thesis excerpts, and call-to-action indicators.
3. **Traffic Funnel & UTM Tracking**:
   - Pins link back to `aviperera.com` with clean attribution tracking:
     `?utm_source=pinterest&utm_medium=social&utm_campaign=syndication`
4. **Zero-Repetition & Deduplication**:
   - Pinned publications are tracked in `state/pinned_history.json`.
   - State is automatically committed back to the repository on each run, ensuring no article is ever pinned twice.
5. **Safe Dry-Run Mode**:
   - If Pinterest API credentials are not yet configured, the engine runs in preview dry-run mode, printing formatting previews and generating cards without failing the GitHub Actions build.

---

## 🛠️ Repository Configuration

To enable live pin publishing, add the following secrets in your repository settings:  
**Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**:

| Secret Name | Required | Description |
| :--- | :---: | :--- |
| `PINTEREST_ACCESS_TOKEN` | **Yes** | Pinterest API v5 access token with `pins:write`, `pins:read`, `boards:read` permissions. |
| `PINTEREST_BOARD_ID` | **Yes** | Numeric/string Board ID where pins should be published. |
| `PINTEREST_DEFAULT_IMAGE_URL` | *Optional* | Fallback public image URL if an article lacks a featured image. |

---

## 📌 How to Obtain Pinterest API Credentials

1. Go to the [Pinterest Developer Portal](https://developers.pinterest.com/).
2. Create an App under your Pinterest account.
3. Generate an Access Token with scopes:
   - `boards:read`
   - `pins:read`
   - `pins:write`
4. Obtain your Board ID:
   - You can query `GET https://api.pinterest.com/v5/boards` with your token or copy the ID from your board's URL / developer dashboard.
5. Save both secrets in this repository.

---

## 🧪 Local Testing

Run unit tests:
```bash
python -m unittest discover tests
```

Run preview dry-run:
```bash
python pinterest_engine.py --dry-run
```

