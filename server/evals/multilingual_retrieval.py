"""Does the policy search find the right policy when a patron asks in another
language? (NEXT_FEATURES.md P1.6: "measure, don't assume".)

The index's embedding model (Pinecone-hosted llama-text-embed-v2) is described
as multilingual. This asks the eval suite's policy questions in English and in
the most common non-English languages spoken at home in the U.S. (Census
ACS): Spanish, Chinese, Vietnamese, Tagalog, Arabic, Korean, Russian. It
reports how often the expected policy record is among the top 3 results, which
is what the agent sees. Pinecone searches only; no model calls.

    uv run python -m evals.multilingual_retrieval
"""

import sys

from app.services.pinecone_service import search_pinecone

TOP_K = 3  # what search_library_policies passes to the agent

# (expected record ids, {language: question}). English matches evals/dataset.py.
QUESTIONS: list[tuple[set[str], dict[str, str]]] = [
    ({"pol3", "pol11"}, {
        "en": "How much are late fees?",
        "es": "¿Cuánto cuestan las multas por retraso?",
        "zh": "逾期罚款是多少？",
        "vi": "Phí trả sách trễ là bao nhiêu?",
        "tl": "Magkano ang multa kapag huli ang pagsauli?",
        "ar": "كم تبلغ غرامات التأخير؟",
        "ko": "연체료는 얼마인가요?",
        "ru": "Какой штраф за просрочку?",
    }),
    ({"pol2"}, {
        "en": "How long can I borrow a book for?",
        "es": "¿Por cuánto tiempo puedo pedir prestado un libro?",
        "zh": "一本书可以借多长时间？",
        "vi": "Tôi có thể mượn sách trong bao lâu?",
        "tl": "Gaano katagal ko puwedeng hiramin ang isang libro?",
        "ar": "ما هي مدة استعارة الكتاب؟",
        "ko": "책은 얼마 동안 빌릴 수 있나요?",
        "ru": "На какой срок можно взять книгу?",
    }),
    ({"pol14"}, {
        "en": "How many times can I renew a book?",
        "es": "¿Cuántas veces puedo renovar un libro?",
        "zh": "一本书可以续借几次？",
        "vi": "Tôi có thể gia hạn sách bao nhiêu lần?",
        "tl": "Ilang beses ko puwedeng i-renew ang isang libro?",
        "ar": "كم مرة يمكنني تجديد استعارة كتاب؟",
        "ko": "책은 몇 번까지 연장할 수 있나요?",
        "ru": "Сколько раз можно продлить книгу?",
    }),
    ({"pol18"}, {
        "en": "I lost my library card. What does a replacement cost?",
        "es": "Perdí mi tarjeta de la biblioteca. ¿Cuánto cuesta reemplazarla?",
        "zh": "我的借书证丢了。补办要多少钱？",
        "vi": "Tôi bị mất thẻ thư viện. Làm lại thẻ mất bao nhiêu tiền?",
        "tl": "Nawala ko ang library card ko. Magkano ang pagpapalit?",
        "ar": "فقدت بطاقة المكتبة. كم تكلفة البطاقة البديلة؟",
        "ko": "도서관 카드를 잃어버렸어요. 재발급 비용은 얼마인가요?",
        "ru": "Я потерял читательский билет. Сколько стоит замена?",
    }),
    ({"pol7"}, {
        "en": "How much does printing cost?",
        "es": "¿Cuánto cuesta imprimir?",
        "zh": "打印多少钱？",
        "vi": "In tài liệu giá bao nhiêu?",
        "tl": "Magkano ang pag-print?",
        "ar": "كم تكلفة الطباعة؟",
        "ko": "인쇄 비용은 얼마인가요?",
        "ru": "Сколько стоит печать?",
    }),
    ({"pol16"}, {
        "en": "How long will you keep my hold before it goes back?",
        "es": "¿Cuánto tiempo guardan mi reserva antes de devolverla?",
        "zh": "预约的书会为我保留多久？",
        "vi": "Sách tôi đặt giữ sẽ được giữ trong bao lâu?",
        "tl": "Gaano katagal itatabi ang aking hold bago ibalik?",
        "ar": "كم من الوقت تحتفظون بالكتاب المحجوز لي قبل إعادته؟",
        "ko": "예약한 책은 얼마 동안 보관해 주나요?",
        "ru": "Сколько дней хранится забронированная книга?",
    }),
    ({"pol17"}, {
        "en": "Can my 10-year-old get their own library card?",
        "es": "¿Mi hijo de 10 años puede tener su propia tarjeta de la biblioteca?",
        "zh": "我10岁的孩子可以办自己的借书证吗？",
        "vi": "Con tôi 10 tuổi có thể làm thẻ thư viện riêng không?",
        "tl": "Puwede bang magkaroon ng sariling library card ang 10 taong gulang kong anak?",
        "ar": "هل يمكن لطفلي البالغ من العمر 10 سنوات الحصول على بطاقة مكتبة خاصة به؟",
        "ko": "열 살 아이도 자기 도서관 카드를 만들 수 있나요?",
        "ru": "Может ли мой десятилетний ребёнок получить свой читательский билет?",
    }),
    ({"pol20"}, {
        "en": "Can I borrow a WiFi hotspot?",
        "es": "¿Puedo pedir prestado un punto de acceso WiFi?",
        "zh": "我可以借无线热点设备吗？",
        "vi": "Tôi có thể mượn thiết bị phát WiFi không?",
        "tl": "Puwede ba akong humiram ng WiFi hotspot?",
        "ar": "هل يمكنني استعارة جهاز نقطة اتصال واي فاي؟",
        "ko": "와이파이 핫스팟을 빌릴 수 있나요?",
        "ru": "Можно ли взять на время мобильную точку доступа Wi-Fi?",
    }),
    ({"pol5", "pol22"}, {
        "en": "Can I book a meeting room?",
        "es": "¿Puedo reservar una sala de reuniones?",
        "zh": "我可以预订会议室吗？",
        "vi": "Tôi có thể đặt phòng họp không?",
        "tl": "Puwede ba akong magpareserba ng meeting room?",
        "ar": "هل يمكنني حجز غرفة اجتماعات؟",
        "ko": "회의실을 예약할 수 있나요?",
        "ru": "Можно ли забронировать переговорную комнату?",
    }),
    ({"pol31"}, {
        "en": "Do you have anything for people with visual impairments?",
        "es": "¿Tienen algo para personas con discapacidad visual?",
        "zh": "你们有为视障人士提供的服务吗？",
        "vi": "Thư viện có gì dành cho người khiếm thị không?",
        "tl": "Mayroon ba kayong para sa mga taong may kapansanan sa paningin?",
        "ar": "هل لديكم خدمات للأشخاص ذوي الإعاقة البصرية؟",
        "ko": "시각 장애인을 위한 서비스가 있나요?",
        "ru": "Есть ли у вас что-нибудь для людей с нарушениями зрения?",
    }),
]
LANGUAGES = ["en", "es", "zh", "vi", "tl", "ar", "ko", "ru"]


def main() -> int:
    hits = {language: 0 for language in LANGUAGES}
    misses: list[str] = []
    for expected, by_language in QUESTIONS:
        for language in LANGUAGES:
            question = by_language[language]
            found = [m["id"] for m in search_pinecone(question, TOP_K)["matches"]]
            if expected & set(found):
                hits[language] += 1
            else:
                misses.append(f"{language}: {question} -> {found} (expected {sorted(expected)})")
    total = len(QUESTIONS)
    print(f"Expected policy in the top {TOP_K}, by language ({total} questions each):")
    for language in LANGUAGES:
        print(f"  {language}: {hits[language]}/{total}")
    if misses:
        print("\nMisses:")
        print("\n".join(f"  {miss}" for miss in misses))
    return 0


if __name__ == "__main__":
    sys.exit(main())
