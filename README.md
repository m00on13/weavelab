# 🧵 WeaveLab

**Turn any image into a string art blueprint you can physically build.**

WeaveLab is a web app that takes a photo or image, runs it through an optimization algorithm, and generates a step-by-step guide for winding thread around a nail frame to recreate that image as string art.

Upload an image → configure your frame → hit generate → get a numbered sequence you can actually follow by hand.

---

## ✨ What It Does

- **Upload any image** — JPG or PNG, with live preprocessing preview
- **Choose your frame shape** — circle, square, rectangle, polygon, or heart
- **Set your pin count** — anywhere from 50 to 1000 nails
- **Generate the string path** — the algorithm figures out the optimal order to wind the thread
- **Watch it draw** — animated canvas shows the art building line by line
- **Follow step-by-step** — guided mode shows you exactly which nail to go to next
- **Export your design** — download as PNG, SVG, CSV, or a printable PDF instruction booklet
- **Save your projects** — come back to any design later

---

## 🖼️ Supported Frame Shapes

| Shape | Description |
|-------|-------------|
| Circle | Classic round frame, evenly spaced pins |
| Square | Pins distributed across 4 equal sides |
| Rectangle | Proportional pin spacing across width and height |
| Polygon | You pick the number of sides |
| Heart | Parametric heart curve with even pin spacing |

---

## 🛠️ Built With

**Frontend**
- React + TypeScript
- Konva.js (canvas rendering)
- Tailwind CSS

**Backend**
- Python + FastAPI
- OpenCV + NumPy (image processing & algorithm)
- Celery + Redis (background job queue)

**Database & Auth**
- Supabase (PostgreSQL + authentication + file storage)

---

## 🚧 Project Status

Currently in development. Building out the core algorithm and API first, then the frontend.

Planned features not yet built:
- Multi-color thread support
- Custom frame shape upload
- Mobile-responsive layout

---

## 💡 How The Algorithm Works

The core idea is a **greedy optimization loop**:

1. Start at any nail
2. Check every other nail — which line would fix the most error between the current canvas and the target image?
3. Draw that line, move to that nail, repeat
4. Stop when no line would improve the image anymore

It's not magic — it's just thousands of tiny decisions, each one making the image a tiny bit more accurate. The algorithm is ported and adapted from [string-art-gen](https://github.com/usedhondacivic/string-art-gen) by Michael Crum.

---

## 📁 Project Structure

```
weavelab/
├── frontend/        # React app
├── backend/
│   ├── app/
│   │   ├── engine/  # The string art algorithm (pure Python)
│   │   ├── routes/  # API endpoints
│   │   └── models/  # Database models
│   └── tests/
└── infra/           # Docker setup
```

---

## 🙏 Credits

Algorithm originally developed by [Michael Crum](https://michael-crum.com/string_art_generator/). This project ports and extends that work into a full-stack web application.
