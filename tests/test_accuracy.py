from sklearn.metrics import accuracy_score


def test_accuracy():
    y_true = [0, 1, 1, 0]
    y_pred = [0, 1, 0, 0]
    acc = accuracy_score(y_true, y_pred)
    assert acc == 0.75
