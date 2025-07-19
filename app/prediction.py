import tensorflow as tf
import pandas as pd
import torch.nn as nn
from app.data_parser import get_data


def predict_from_earth_access(model, start_date, end_date):
    """
    Predict the data from the Earth Access API
    """
    data = get_data(start_date, end_date)
    return predict(model, data)


def train_model(model, data):
    """
    Train the model
    """

    model.fit(data, data, epochs=500)
    return model


def create_adam_model():
    """
    Create the model
    """
    model = tf.keras.models.Sequential(
        [tf.keras.layers.Dense(units=1, input_shape=[1])]
    )

    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )

    return model


def sigmoid_model():
    """
    Create the sigmoid model
    """
    model = nn.Sequential(
        nn.Linear(input_size, 64),
        nn.ReLU(),
        nn.Linear(64, 32),
        nn.ReLU(),
        nn.Linear(32, 1),
        nn.Sigmoid(),
    )
    return model
