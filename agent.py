"""Ohmicly Content Agent
প্রতি সপ্তাহে: (১) গুগল সার্চ দিয়ে রিসার্চ -> (২) LinkedIn, Facebook, YouTube পোস্ট ড্রাফট।
শুধু Python standard library লাগে, কিছু install করতে হয় না।
"""
import datetime
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
ROOT = pathlib.Path(__file__).parent
POSTS = ROOT / "posts"
POSTS.mkdir(exist_ok=True)


def call_gemini(prompt, search=False, retries=4):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if search:
        body["tools"] = [{"google_search": {}}]
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "x-goog-api-key": API_KEY}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < retries - 1:
                time.sleep(30 * (attempt + 1))
                continue
            raise SystemExit(f"Gemini error {e.code}: {e.read().decode()[:500]}")
    cand = out["candidates"][0]
    text = "".join(p.get("text", "") for p in cand["content"]["parts"])
    sources = []
    for ch in cand.get("groundingMetadata", {}).get("groundingChunks", []):
        web = ch.get("web")
        if web:
            sources.append((web.get("title", "source"), web.get("uri", "")))
    return text, sources


def past_topics():
    files = sorted(POSTS.glob("*.md"))[-6:]
    lines = []
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("TOPIC:"):
                lines.append(line)
    return "\n".join(lines) or "(এখনো কোনো পোস্ট হয়নি)"


def main():
    today = datetime.date.today().isoformat()
    config = (ROOT / "config.md").read_text(encoding="utf-8")
    history = past_topics()

    research_prompt = f"""তুমি Ohmicly-র কনটেন্ট রিসার্চার। নিচের প্রোফাইল পড়ো।

{config}

আজকের তারিখ: {today}

গুগল সার্চ ব্যবহার করে এই সপ্তাহের জন্য রিসার্চ করো। বাংলাদেশের RMG/ফ্যাক্টরির ইলেকট্রিক্যাল ফ্রেশারদের জন্য কী কাজে লাগবে:
1. সাম্প্রতিক খবর/আপডেট: RSC, নিরাপন, BNBC 2020, ফ্যাক্টরি ইলেকট্রিক্যাল সেফটি, অডিট, Accord/Alliance/ব্র্যান্ড রিকোয়ারমেন্ট
2. ফ্রেশার ইঞ্জিনিয়াররা কী প্রশ্ন করছে (YouTube ভিডিও/কমেন্ট, ফোরাম, পাবলিক ডিসকাশন)
3. LinkedIn ও Facebook-এ এই বিষয়ে কোন ধরনের পোস্ট জনপ্রিয় (পাবলিক সার্চ রেজাল্ট থেকে)
4. কোন টপিকে ভালো বাংলা/ইংরেজি কনটেন্টের অভাব আছে (gap)

আগের টপিক (এগুলো রিপিট করবে না):
{history}

আউটপুট: ৫টি টপিক আইডিয়া। প্রতিটির জন্য: কেন এখন প্রাসঙ্গিক, কোন প্রশ্নের উত্তর দেয়, কোন সোর্স থেকে পেয়েছ। তথ্য না পেলে বানিয়ে বলবে না।"""

    research, sources = call_gemini(research_prompt, search=True)

    write_prompt = f"""তুমি Ohmicly-র মালিকের ঘোস্টরাইটার। নিচে প্রোফাইল ও রিসার্চ আছে।

{config}

রিসার্চ:
{research}

এই সপ্তাহের জন্য ঠিক ৩টি পোস্ট লেখো। ৩টি আলাদা টপিক নিয়ে (রিসার্চের সেরা ৩টি):

### পোস্ট ১: LinkedIn
- ইংরেজি-বাংলা মিক্স, প্রফেশনাল কিন্তু সহজ। ১২০-২২০ শব্দ।
- প্রথম লাইনে হুক। ছোট প্যারাগ্রাফ। শেষে একটা প্রশ্ন বা CTA।

### পোস্ট ২: Facebook
- বাংলা প্রধান, ফ্রেন্ডলি। ১০০-১৮০ শব্দ।
- শেষে ফ্রি টেমপ্লেট/কোর্সের দিকে নিয়ে যাওয়ার CTA (Ohmicly)।

### পোস্ট ৩: YouTube
- ৫-৭ মিনিটের ভিডিওর স্ক্রিপ্ট: টাইটেল (৩টি অপশন), থাম্বনেইল টেক্সট, হুক (প্রথম ১৫ সেকেন্ড), পয়েন্ট অনুযায়ী স্ক্রিপ্ট, ডিস্ক্রিপশন, ট্যাগ।

প্রতিটি পোস্টের আগে এক লাইনে লিখবে: `TOPIC: <টপিকের নাম>`

কঠোর নিয়ম:
- কোনো সংখ্যা, ধারা নম্বর বা রেগুলেশন বানিয়ে লিখবে না। নিশ্চিত না হলে `[যাচাই করুন]` লিখে দেবে।
- BNBC বা RSC-র নির্দিষ্ট ক্লজ উদ্ধৃত করলে সেটা `[যাচাই করুন]` চিহ্নিত করবে।
- অন্য কারো পোস্ট বা ভিডিও কপি করবে না। আইডিয়া নেবে, ভাষা নিজের।
- সবার শেষে "## মালিকের জন্য নোট" সেকশনে লিখবে: কোন পোস্টে কোন ফাইল/ছবি/স্ক্রিনশট যোগ করলে ভালো হবে, আর কোন তথ্য আগে যাচাই করতে হবে।"""

    posts, _ = call_gemini(write_prompt)

    src_lines = "\n".join(f"- [{t}]({u})" for t, u in dict.fromkeys(sources)) or "- (সোর্স পাওয়া যায়নি)"
    out = f"""# Ohmicly কনটেন্ট ড্রাফট: {today}

> এগুলো ড্রাফট। পোস্ট করার আগে নিজে পড়ে, তথ্য যাচাই করে নিন।

{posts}

---

## রিসার্চ সারাংশ
{research}

## সোর্স
{src_lines}
"""
    path = POSTS / f"{today}.md"
    path.write_text(out, encoding="utf-8")
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
