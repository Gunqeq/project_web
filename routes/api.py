from flask import Blueprint, request, jsonify, render_template
from services.route_service import route_suggestions
from services.province_service import search_by_province

api_bp = Blueprint("api", __name__)

@api_bp.route("/route_suggestions", methods=["POST"])
def api_route_suggestions():
    data = request.json
    return jsonify(route_suggestions(
        data.get("origin"),
        data.get("destination"),
        data.get("categories"),
        mode=data.get("mode", "driving")
    ))

@api_bp.route("/search_by_province", methods=["POST"])
def api_search_by_province():
    data = request.json
    return jsonify(search_by_province(
        data.get("province"),
        data.get("categories")
    ))

@api_bp.route("/")
def index():
    return render_template("index.html")

@api_bp.route("/client_log", methods=["POST"])
def client_log():
    data = request.json or {}
    print("CLIENT LOG:", data)  
    return {"status": "ok"}