from flask import Flask, request, jsonify, render_template
import pronouncing
import os
import json
import re
from difflib import SequenceMatcher
from Levenshtein import ratio

app = Flask(__name__)

# หน้าหลัก
@app.route('/')
def home():
    return render_template('index.html')

# หน้าผู้ใช้
@app.route('/user')
def user():
    return render_template('user.html')

# หน้าความยาก
@app.route('/difficulty')
def difficulty():
    return render_template('difficulty.html')

# หน้าตั้งค่า
@app.route('/settings')
def settings():
    return render_template('settings.html')

# หน้าทดสอบ
@app.route('/test')
def speech_test():
    return render_template('test.html')

# API สำหรับดึงประโยคทดสอบ
@app.route('/get-test-sentences', methods=['GET'])
def get_test_sentences():
    try:
        json_path = os.path.join(os.getcwd(), "static", "sentences.json")
        if not os.path.exists(json_path):
            return jsonify({"error": "sentences.json file not found!"}), 404

        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})

# API วิเคราะห์การออกเสียง
@app.route('/analyze', methods=['POST'])
def analyze_pronunciation():
    try:
        data = request.json
        target_sentence = data.get('target_sentence', '').lower().strip()
        user_speech = data.get('user_speech', '').lower().strip()
        strictness = data.get('strictness', 'medium')

        # การประมวลผลประโยค (ลบเครื่องหมายวรรคตอน)
        def preprocess_sentence(sentence):
            return re.sub(r'[^\w\s]', '', sentence).strip()

        target_sentence = preprocess_sentence(target_sentence)
        user_speech = preprocess_sentence(user_speech)

        # แปลงคำเป็นเสียงพยางค์
        def sentence_to_phonemes(sentence):
            phonemes = [pronouncing.phones_for_word(word)[0] if pronouncing.phones_for_word(word) else "" for word in sentence.split()]
            return phonemes

        target_phonemes = sentence_to_phonemes(target_sentence)
        user_phonemes = sentence_to_phonemes(user_speech)

        # การจัดการข้อผิดพลาดสำหรับเสียงพยางค์ที่หายไป
        if not target_phonemes or not user_phonemes or len(target_phonemes) == 0 or len(user_phonemes) == 0:
            return jsonify({"error": "Phoneme extraction failed. Check input sentences."}), 400

        # การปรับปรุงการคำนวณความคล้ายคลึงของเสียงพยางค์
        def phoneme_similarity(phoneme1, phoneme2):
            """Combines Levenshtein ratio and SequenceMatcher for accurate phoneme comparison."""
            seq_match_score = SequenceMatcher(None, phoneme1, phoneme2).ratio()
            lev_score = ratio(phoneme1, phoneme2)
            return (seq_match_score + lev_score) / 2  # Average score of both methods

        # การเปรียบเทียบเสียงพยางค์
        correct = sum(phoneme_similarity(t, u) for t, u in zip(target_phonemes, user_phonemes))
        total = len(target_phonemes)
        accuracy = (correct / total) * 100 if total > 0 else 0

        # ส่งเสริมการจับคู่ที่แทบจะสมบูรณ์แบบ (ให้คะแนน 100% สมบูรณ์)
        if accuracy > 95:
            accuracy = 100

        # การใช้ความเข้มงวด (ใช้เฉพาะเมื่อมีข้อผิดพลาด)
        if strictness == "high" and accuracy < 95:
            accuracy *= 0.90  # 10% penalty if below 95%
        elif strictness == "very_high" and accuracy < 98:
            accuracy *= 0.85  # 15% penalty if below 98%

        # ให้แน่ใจว่าความแม่นยำอยู่ระหว่าง 0-100%
        accuracy = max(0, min(accuracy, 100))

        # บันทึกการตรวจสอบข้อผิดพลาด (ลบออกเมื่อใช้จริง)
        print(f"Strictness: {strictness}, Accuracy Before Scaling: {accuracy}%")

        return jsonify({
            "target_phonemes": target_phonemes,
            "user_phonemes": user_phonemes,
            "accuracy": round(accuracy, 2),
            "strictness": strictness
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
