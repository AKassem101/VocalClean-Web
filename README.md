# VocalClean Web 🎙️

واجهة عربية لفصل الصوت البشري عن الموسيقى باستخدام Demucs. واجهة GitHub Pages ثابتة، ومحرك المعالجة FastAPI منفصل.

## نشر الواجهة على GitHub Pages

1. افتح **Settings → Pages → Build and deployment** واختر **Deploy from a branch**، ثم **main** و **/(root)**، واضغط **Save**.
2. انتظر النشر، ثم افتح https://AKassem101.github.io/VocalClean-Web/

> نشر الواجهة وحدها لا يشغل فصل الصوت. يلزم خادم Backend يعمل عليه Demucs.

## تشغيل محرك المعالجة محليًا (Windows)

يحتاج Python 3.11 وFFmpeg متاحًا في PATH، ومساحة لتنزيل نموذج Demucs.

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ALLOWED_ORIGINS="http://localhost:5500,https://AKassem101.github.io"
uvicorn main:app --host 127.0.0.1 --port 8000
```

يمكنك تشغيل الواجهة محليًا من جذر المشروع باستخدام `python -m http.server 5500` ثم إدخال `http://localhost:8000` في حقل API.

## نشر Backend على خادم

يمكن بناء Docker من مجلد `backend/`:

```bash
docker build -t vocalclean-api backend
docker run -p 8000:8000 -e ALLOWED_ORIGINS=https://AKassem101.github.io vocalclean-api
```

يحتاج الخادم إلى ذاكرة ومعالج ومساحة تخزين مناسبة، وHTTPS صالح للموقع المنشور على GitHub Pages. الاستضافات المجانية محدودة وقد لا تناسب Demucs.

## ملاحظات تشغيل وأمان

- الملفات المرفوعة تُعالج على الخادم وليس داخل المتصفح.
- هذه نسخة أولية للتجربة وليست خدمة إنتاج عامة: لا يوجد تسجيل دخول أو تحديد معدل الطلبات أو تنظيف تلقائي للملفات، وتُخزن حالة المهام في ذاكرة العملية. أضف هذه الخصائص قبل فتح الخادم للعامة.
- حجم الملف الأقصى 25MB؛ الملفات الناتجة WAV وقد تكون كبيرة. قد تستغرق المعالجة دقائق.
- أول معالجة تتطلب تنزيل نموذج Demucs على الخادم.
- استخدم الملفات التي تملك حق معالجتها.
