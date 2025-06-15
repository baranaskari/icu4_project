from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import requests
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///favorites.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

SPOONACULAR_API_KEY = '4356ddf86f3142e987a668758ea019ae'

class FavoriteRecipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, unique=True)
    title = db.Column(db.String(200))
    image = db.Column(db.String(300))
    instructions = db.Column(db.Text)
    ingredients = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.recipe_id,
            "title": self.title,
            "image": self.image,
            "instructions": self.instructions,
            "extendedIngredients": [{"original": i} for i in self.ingredients.split('\n')]
        }

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/favorites")
def favorites_page():
    return render_template("favorites.html")

@app.route("/recipes", methods=["POST"])
def get_recipes():
    data = request.get_json()
    ingredients = data.get("ingredients")
    res = requests.get(
        "https://api.spoonacular.com/recipes/findByIngredients",
        params={"ingredients": ingredients, "number": 5, "apiKey": SPOONACULAR_API_KEY}
    )
    recipe_list = res.json()

    detailed = []
    for r in recipe_list:
        r_id = r["id"]
        res_detail = requests.get(
            f"https://api.spoonacular.com/recipes/{r_id}/information",
            params={"includeNutrition": False, "apiKey": SPOONACULAR_API_KEY}
        )
        detailed.append(res_detail.json())

    return jsonify(detailed)

@app.route("/api/favorites", methods=["GET"])
def get_favorites():
    return jsonify([r.to_dict() for r in FavoriteRecipe.query.all()])

@app.route("/api/favorites", methods=["POST"])
def add_favorite():
    data = request.get_json()
    if FavoriteRecipe.query.filter_by(recipe_id=data["id"]).first():
        return jsonify({"message": "Already saved"}), 409

    recipe = FavoriteRecipe(
        recipe_id=data["id"],
        title=data["title"],
        image=data["image"],
        instructions=data.get("instructions", "No instructions provided."),
        ingredients="\n".join(i["original"] for i in data["extendedIngredients"])
    )
    db.session.add(recipe)
    db.session.commit()
    return jsonify({"message": "Saved"}), 201

@app.route("/api/favorites/<int:recipe_id>", methods=["DELETE"])
def delete_favorite(recipe_id):
    r = FavoriteRecipe.query.filter_by(recipe_id=recipe_id).first()
    if r:
        db.session.delete(r)
        db.session.commit()
        return jsonify({"message": "Deleted"}), 200
    return jsonify({"message": "Not found"}), 404

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
