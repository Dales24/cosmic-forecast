from flask import Flask, render_template_string, request
from data_parser import get_data

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
{% if data_result %}
  <h3>get_data Result:</h3>
  <pre>{{ data_result }}</pre>
{% endif %}
"""


@app.route("/", methods=["GET", "POST"])
def index():
    location = prediction = data_result = None
    if request.method == "POST":
        location = request.form.get("location")
        prediction = request.form.get("prediction")
        # Call get_data with the form arguments
        try:
            data_result = get_data(location, prediction)
        except Exception as e:
            data_result = f"Error: {e}"
    return render_template_string(
        HTML_FORM, location=location, prediction=prediction, data_result=data_result
    )


if __name__ == "__main__":
    app.run(debug=True)
