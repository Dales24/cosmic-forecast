# cosmic_forcast
A prediction system based on NASA earth data

This project aims to train a model on NASA data for predicting space objects and their trajectory. The goal is to compare model and algorithm accuracy, and potentially use ensemble methods to estimate probabilities.

## Demo

A simple web interface is available to input arguments for location and prediction.

## Setup Steps
1. Create a Python virtual environment (e.g., using `pyenv` or `venv`).
2. Activate the environment.
3. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the prediction script or web interface as needed.

### To run the web interface:
```bash
python app/interface.py
```
Then open your browser to [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## Testing

To run tests:
```bash
pytest
```

