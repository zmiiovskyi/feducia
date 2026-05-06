import re
import wave
import whisper


MODEL = whisper.load_model("base")

WORD_RE = re.compile(r"[A-Za-z']+")

FILLER_WORDS = {
    "uh",
    "um",
    "erm",
    "ah",
    "like",
    "so",
    "actually",
    "basically",
    "right",
}

FILLER_PHRASES = [
    "you know",
    "i mean",
    "kind of",
    "sort of",
]


def get_audio_duration(audio_path):
    with wave.open(audio_path, "rb") as audio_file:
        frames = audio_file.getnframes()
        rate = audio_file.getframerate()

        if rate == 0:
            return 0

        return round(frames / float(rate), 2)


def count_fillers(text, words):
    text_lower = text.lower()
    fillers = []

    for phrase in FILLER_PHRASES:
        count = text_lower.count(phrase)
        for _ in range(count):
            fillers.append(phrase)

    for word in words:
        if word.lower() in FILLER_WORDS:
            fillers.append(word.lower())

    return fillers


def count_repeats(words):
    repeats = []
    for i in range(1, len(words)):
        if words[i].lower() == words[i - 1].lower():
            repeats.append(words[i].lower())
    return repeats


def analyze_pauses(segments):
    pauses = []

    for i in range(1, len(segments)):
        prev_end = segments[i - 1].get("end", 0)
        curr_start = segments[i].get("start", 0)

        pause = curr_start - prev_end
        if pause > 0:
            pauses.append(round(pause, 2))

    if not pauses:
        return {
            "pause_count": 0,
            "long_pause_count": 0,
            "average_pause": 0,
            "max_pause": 0,
        }

    long_pause_count = 0
    for pause in pauses:
        if pause >= 1.0:
            long_pause_count += 1

    average_pause = round(sum(pauses) / len(pauses), 2)
    max_pause = round(max(pauses), 2)

    return {
        "pause_count": len(pauses),
        "long_pause_count": long_pause_count,
        "average_pause": average_pause,
        "max_pause": max_pause,
    }


def calculate_confidence(words_per_minute, filler_ratio, repeat_count, long_pause_count):
    score = 10

    if words_per_minute < 100:
        score -= 2
    elif words_per_minute > 180:
        score -= 1

    if filler_ratio >= 0.10:
        score -= 3
    elif filler_ratio >= 0.06:
        score -= 2
    elif filler_ratio >= 0.03:
        score -= 1

    if repeat_count >= 4:
        score -= 2
    elif repeat_count >= 2:
        score -= 1

    if long_pause_count >= 6:
        score -= 3
    elif long_pause_count >= 3:
        score -= 2
    elif long_pause_count >= 1:
        score -= 1

    if score < 0:
        score = 0

    if score > 10:
        score = 10

    return score


def detect_tension(words_per_minute, filler_ratio, repeat_count, long_pause_count):
    signs = []

    if words_per_minute > 180:
        signs.append("fast_speech")

    if filler_ratio >= 0.06:
        signs.append("many_fillers")

    if repeat_count >= 2:
        signs.append("repetitions")

    if long_pause_count >= 3:
        signs.append("many_long_pauses")

    return len(signs) >= 2, signs


def build_feedback(
    confidence_score,
    words_per_minute,
    filler_count,
    filler_ratio,
    repeat_count,
    pause_data,
    is_tense,
):
    strengths = []
    weaknesses = []
    advice = []

    if confidence_score >= 8:
        strengths.append("Your speech sounds stable and confident overall.")

    if 110 <= words_per_minute <= 160:
        strengths.append("Your speaking pace is comfortable and easy to follow.")

    if filler_count == 0:
        strengths.append("You speak clearly without noticeable filler words.")
    elif filler_ratio < 0.03:
        strengths.append("You use only a small number of filler words.")

    if pause_data["long_pause_count"] == 0:
        strengths.append("Your delivery is smooth, with no strong signs of hesitation.")

    if repeat_count == 0:
        strengths.append("Your wording sounds steady, without repeated words.")

    if words_per_minute < 100:
        weaknesses.append("Your pace is rather slow, which may reduce energy and confidence.")
        advice.append("Try to keep a slightly quicker pace, especially at the beginning of sentences.")

    elif words_per_minute > 180:
        weaknesses.append("Your pace is quite fast, which may make you sound nervous or rushed.")
        advice.append("Slow down slightly and give each sentence a clearer ending.")

    if filler_ratio >= 0.06:
        weaknesses.append("Filler words appear quite often and reduce the clarity of your message.")
        advice.append("Pause silently instead of filling space with words like 'um', 'like', or 'you know'.")
    elif filler_ratio >= 0.03:
        weaknesses.append("There are some filler words that slightly interrupt the flow.")
        advice.append("Focus on cleaner transitions between ideas.")

    if repeat_count >= 2:
        weaknesses.append("Repeated words suggest moments of hesitation or loss of flow.")
        advice.append("Take a short pause before the next idea instead of restarting the phrase.")

    if pause_data["long_pause_count"] >= 3:
        weaknesses.append("Several long pauses suggest hesitation or uncertainty.")
        advice.append("Practice grouping your ideas into shorter chunks so pauses feel more intentional.")
    elif pause_data["long_pause_count"] >= 1:
        weaknesses.append("A few long pauses may weaken the feeling of confidence.")
        advice.append("Prepare the opening and key transitions in advance.")

    if is_tense:
        weaknesses.append("There are signs of tension in your delivery, such as pace, pauses, or filler patterns.")
        advice.append("Before speaking, take one slow breath and begin with a calm first sentence.")

    if confidence_score >= 8:
        summary = "Your speech sounds confident, clear, and fairly controlled."
    elif confidence_score >= 5:
        summary = "Your speech is understandable and reasonably stable, but there are a few signs of hesitation."
    else:
        summary = "Your speech shows noticeable signs of uncertainty, and it would benefit from a steadier pace and cleaner delivery."

    if not strengths:
        strengths.append("Your recording provides a good base for further improvement.")

    if not weaknesses:
        weaknesses.append("No major speaking issues were detected in this recording.")

    if not advice:
        advice.append("Keep practicing with short presentations to make your delivery even more natural and stable.")

    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "advice": advice,
    }


def build_report(feedback, is_tense):
    parts = [feedback["summary"]]

    if feedback["strengths"]:
        parts.append("Strong points: " + " ".join(feedback["strengths"]))

    if feedback["weaknesses"]:
        parts.append("Areas to improve: " + " ".join(feedback["weaknesses"]))

    if feedback["advice"]:
        parts.append("Advice: " + " ".join(feedback["advice"]))

    if is_tense:
        parts.append("Your speech also shows some signs of nervousness.")
    else:
        parts.append("No strong signs of nervousness were detected.")

    return " ".join(parts)


def analyze_audio(audio_path):
    duration = get_audio_duration(audio_path)

    result = MODEL.transcribe(
        audio_path,
        fp16=False,
        verbose=False,
        condition_on_previous_text=False,
        temperature=0,
    )

    text = result.get("text", "").strip()
    segments = result.get("segments", [])

    words = WORD_RE.findall(text)
    words_count = len(words)

    if words_count == 0:
        return {
            "success": True,

            "duration_seconds": duration,

            "words_count": 0,
            "words_per_minute": 0,

            "confidence_score": 0,
            "confidence": "Not detected",

            "pace": "Not detected",

            "filler_count": 0,
            "filler_ratio": 0,
            "fillers": "Not detected",

            "feedback": {
                "summary": "No speech was detected in the recording.",
                "strengths": [],
                "weaknesses": [],
                "advice": [
                    "Try speaking clearly during the recording."
                ]
            }
        }

    if duration > 0:
        words_per_minute = round((words_count / duration) * 60, 1)
    else:
        words_per_minute = 0

    fillers = count_fillers(text, words)
    filler_count = len(fillers)

    if words_count > 0:
        filler_ratio = round(filler_count / words_count, 3)
    else:
        filler_ratio = 0

    repeats = count_repeats(words)
    repeat_count = len(repeats)

    pause_data = analyze_pauses(segments)

    confidence_score = calculate_confidence(
        words_per_minute=words_per_minute,
        filler_ratio=filler_ratio,
        repeat_count=repeat_count,
        long_pause_count=pause_data["long_pause_count"],
    )

    is_tense, tension_signs = detect_tension(
        words_per_minute=words_per_minute,
        filler_ratio=filler_ratio,
        repeat_count=repeat_count,
        long_pause_count=pause_data["long_pause_count"],
    )

    feedback = build_feedback(
        confidence_score=confidence_score,
        words_per_minute=words_per_minute,
        filler_count=filler_count,
        filler_ratio=filler_ratio,
        repeat_count=repeat_count,
        pause_data=pause_data,
        is_tense=is_tense,
    )

    report = build_report(feedback, is_tense)

    if confidence_score >= 8:
        confidence = "High"
    elif confidence_score >= 5:
        confidence = "Medium"
    else:
        confidence = "Low"

    if words_per_minute < 100:
        pace = "Slow"
    elif words_per_minute > 180:
        pace = "Fast"
    else:
        pace = "Good"

    if filler_count == 0:
        fillers = "None"
    elif filler_ratio < 0.03:
        fillers = "Few"
    else:
        fillers = "Many"

    return {
        "success": True,
        "text": text,
        "duration_seconds": duration,
        "words_count": words_count,
        "words_per_minute": words_per_minute,
        "filler_words": fillers,
        "filler_count": filler_count,
        "filler_ratio": filler_ratio,
        "repeated_words": repeats,
        "repeat_count": repeat_count,
        "pause_analysis": pause_data,
        "confidence_score": confidence_score,
        "sounds_nervous": is_tense,
        "tension_signs": tension_signs,
        "feedback": feedback,
        "report": report,
        "confidence": confidence,
        "pace": pace,
        "fillers": fillers,
    }