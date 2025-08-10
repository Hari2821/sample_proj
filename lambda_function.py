import os, json, boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
students_table = dynamodb.Table(os.environ["STUDENTS_TABLE"])
faqs_table = dynamodb.Table(os.environ["FAQS_TABLE"])

def lex_response(text, session_attributes=None):
    return {
        "sessionState": {
            "dialogAction": {"type": "Close"},
            "intent": {"name": "FulfilledIntent", "state": "Fulfilled"}
        },
        "messages": [{"contentType": "PlainText", "content": text}],
        "sessionAttributes": session_attributes or {}
    }

def get_slot(event, slot_name):
    try:
        return event["sessionState"]["intent"]["slots"][slot_name]["value"]["interpretedValue"]
    except Exception:
        return None

def get_intent_name(event):
    return event["sessionState"]["intent"]["name"]

def handle_get_student_info(event):
    sid = get_slot(event, "student_id")
    if not sid:
        return lex_response("Please provide your Student ID (e.g., S2023001).")
    res = students_table.get_item(Key={"student_id": sid})
    item = res.get("Item")
    if not item:
        return lex_response(f"I couldn't find a student with ID {sid}. Please check and try again.")
    msg = (
        f"Name: {item['name']}\n"
        f"Department: {item['department']} | Year: {item['year']}\n"
        f"Email: {item['email']} | Phone: {item['phone']}\n"
        f"Advisor: {item['advisor']} | Fees Due: ₹{item['fees_due']}"
    )
    return lex_response(msg)

def handle_faq(event):
    topic = get_slot(event, "topic")
    if topic:
        scan = faqs_table.scan(
            FilterExpression=Attr("tags").contains(topic.lower())
                            | Attr("question").contains(topic)
                            | Attr("answer").contains(topic)
        )
    else:
        scan = faqs_table.scan(Limit=5)
    items = scan.get("Items", [])
    if not items:
        return lex_response("I couldn't find that. Try asking like: 'bonafide certificate' or 'academic calendar'.")
    faq = items[0]
    return lex_response(f"Q: {faq['question']}\nA: {faq['answer']}")

def handle_fallback(event):
    return lex_response("Sorry, I didn't get that. Try: 'student info S2023001' or 'bonafide certificate'.")

def lambda_handler(event, context):
    intent = get_intent_name(event)
    if intent == "GetStudentInfo":
        return handle_get_student_info(event)
    elif intent == "FAQ":
        return handle_faq(event)
    else:
        return handle_fallback(event)
