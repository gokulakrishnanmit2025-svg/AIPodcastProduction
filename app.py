
from flask import Flask, render_template, request, send_file
from gtts import gTTS
from io import BytesIO
import requests

app = Flask(__name__)

# Ollama configuration
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "gemma2:2b"
OLLAMA_TIMEOUT = 300

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi"
}


def generate_podcast_script(topic, duration, language="en"):
    """Generate a podcast script using the local Ollama model."""

    language_names = {
        "en": "English",
        "ta": "Tamil",
        "hi": "Hindi"
    }

    if language not in language_names:
        language = "en"

    selected_language = language_names[language]

    prompt = f"""
You are a professional podcast producer and scriptwriter.

Create a complete podcast episode about:
{topic}

Target duration: approximately {duration} minutes.

Write the entire podcast in {selected_language}.

Requirements:
1. Start with an attractive, creative episode title.
2. Begin with an engaging introduction.
3. Explain the topic clearly and accurately.
4. Include useful facts and examples.
5. Use natural language suitable for speaking aloud.
6. Organize the script into clear sections.
7. Include smooth transitions between sections.
8. End with a conclusion and thank the listeners.
9. Return only the complete podcast script.
10. Do not include instructions for the narrator.

All spoken content must be in {selected_language}.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        },
        timeout=OLLAMA_TIMEOUT
    )

    response.raise_for_status()

    result = response.json()
    script = result.get("response", "").strip()

    if not script:
        raise ValueError(
            "The AI returned an empty script. Please try again."
        )

    return script


@app.route("/", methods=["GET", "POST"])
def home():
    script = ""
    topic = ""
    duration = 3
    language = "en"
    error = ""

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        language = request.form.get("language", "en").strip()

        try:
            duration = int(request.form.get("duration", "3"))

            if not topic:
                raise ValueError(
                    "Please enter a podcast topic."
                )

            if len(topic) > 200:
                raise ValueError(
                    "The topic must be 200 characters or fewer."
                )

            if not 1 <= duration <= 10:
                raise ValueError(
                    "Choose a duration between 1 and 10 minutes."
                )

            if language not in SUPPORTED_LANGUAGES:
                raise ValueError(
                    "Please select English, Tamil, or Hindi."
                )

            script = generate_podcast_script(
                topic,
                duration,
                language
            )

        except ValueError as exc:
            error = str(exc)

        except requests.RequestException:
            error = (
                "Could not connect to Ollama. Make sure Ollama is "
                "running and the gemma2:2b model is installed."
            )

        except Exception:
            app.logger.exception(
                "Podcast script generation failed."
            )
            error = (
                "Something went wrong while generating the script. "
                "Check the terminal for details."
            )

    return render_template(
        "index.html",
        script=script,
        topic=topic,
        duration=duration,
        language=language,
        error=error,
        languages=SUPPORTED_LANGUAGES
    )


@app.route("/download-script", methods=["POST"])
def download_script():
    """Download the podcast script as a UTF-8 text file."""

    script = request.form.get("script", "").strip()

    if not script:
        return "No podcast script was provided.", 400

    script_file = BytesIO(script.encode("utf-8"))
    script_file.seek(0)

    return send_file(
        script_file,
        mimetype="text/plain; charset=utf-8",
        as_attachment=True,
        download_name="podcast_script.txt"
    )


@app.route("/download-audio", methods=["POST"])
def download_audio():
    """Convert the podcast script into an MP3 file."""

    script = request.form.get("script", "").strip()
    language = request.form.get("language", "en").strip()

    if not script:
        return "No podcast script was provided.", 400

    if len(script) > 50000:
        return (
            "The podcast script is too long for this download.",
            400
        )

    if language not in SUPPORTED_LANGUAGES:
        return "Unsupported audio language.", 400

    try:
        audio = BytesIO()

        tts = gTTS(
            text=script,
            lang=language,
            slow=False
        )

        tts.write_to_fp(audio)
        audio.seek(0)

        return send_file(
            audio,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name=f"podcast_episode_{language}.mp3"
        )

    except Exception:
        app.logger.exception(
            "Podcast audio generation failed."
        )

        return (
            "Audio generation failed. Check your internet connection "
            "and try again.",
            500
        )


if __name__ == "__main__":
    app.run(debug=True)