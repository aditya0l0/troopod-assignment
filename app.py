from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
import base64
import json
from PIL import Image
import io
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# ---- PASTE YOUR OPENROUTER API KEY HERE ----
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

def scrape_page(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else ""
        headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        buttons = [b.get_text(strip=True) for b in soup.find_all(["button", "a"])]
        return {
            "title": title,
            "headings": headings[:10],
            "paragraphs": paragraphs[:10],
            "buttons": buttons[:10]
        }
    except Exception as e:
        return {"error": str(e)}

def image_to_base64(image_file):
    img = Image.open(image_file)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/enhance", methods=["POST"])
def enhance():
    image_file = request.files.get("ad_image")
    landing_url = request.form.get("landing_url")

    if not image_file or not landing_url:
        return jsonify({"error": "Please provide both image and URL."})

    # Scrape page
    page_data = scrape_page(landing_url)
    if "error" in page_data:
        return jsonify({"error": f"Could not scrape URL: {page_data['error']}"})

    # Convert image
    img_base64 = image_to_base64(image_file)

    # Build prompt
    prompt = f"""You are a world-class CRO (Conversion Rate Optimization) expert.

I will give you:
1. An ad creative image
2. A landing page's current content

Your Tasks:
- Analyze the ad creative: What is the message? Tone? CTA? Product/offer shown?
- Rewrite the landing page content to match the ad creative
- Keep the SAME page structure, only enhance the copy
- Make headline, subheadline, CTA buttons, and body text consistent with the ad
- Apply CRO best practices: clear value proposition, urgency, social proof, strong CTA

Current Landing Page Content:
Title: {page_data['title']}
Headings: {page_data['headings']}
Paragraphs: {page_data['paragraphs']}
Buttons/CTAs: {page_data['buttons']}

Output a complete enhanced HTML page with:
1. Rewritten content personalized to match the ad creative
2. Clean, modern styling using inline CSS
3. All original sections preserved but copy enhanced
4. A prominent CTA matching the ad's offer
5. Mobile responsive design

Only output raw HTML code, no explanations, no markdown backticks."""

    # Call OpenRouter
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        data=json.dumps({
            "model": "openrouter/auto",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        })
    )

    result = response.json()

    if "error" in result:
        return jsonify({"error": result["error"]["message"]})

    enhanced_html = result["choices"][0]["message"]["content"]

    # Clean markdown
    if "```html" in enhanced_html:
        enhanced_html = enhanced_html.split("```html")[1].split("```")[0]
    elif "```" in enhanced_html:
        enhanced_html = enhanced_html.split("```")[1].split("```")[0]

    return jsonify({"html": enhanced_html})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)