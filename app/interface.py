from flask import Flask, render_template_string, request

app = Flask(__name__)

HTML_FORM = """
<!doctype html>
<title>Prediction Input</title>
<h2>Enter Arguments</h2>
<form method="post">
  Location: <input type="text" name="location"><br><br>
  Prediction: <input type="text" name="prediction"><br><br>
  <input type="submit" value="Submit">
</form>
{% if location and prediction %}
  <h3>Submitted Values:</h3>
  <p>Location: {{ location }}</p>
  <p>Prediction: {{ prediction }}</p>
{% endif %}
"""


@app.route("/", methods=["GET", "POST"])
def index():
    location = prediction = None
    if request.method == "POST":
        location = request.form.get("location")
        prediction = request.form.get("prediction")
    return render_template_string(HTML_FORM, location=location, prediction=prediction)


if __name__ == "__main__":
    app.run(debug=True)
