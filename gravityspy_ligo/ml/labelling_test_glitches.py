import tensorflow as tf
from .GS_utils import concatenate_views
from .GS_utils import GS_new
from keras.models import load_model
from PIL import Image
from keras.applications.vgg16 import preprocess_input

import numpy
import os

'''
By Sara Bahaadini and Neda Rohani, IVPL, Northwestern University.
This function reads the trained ML classifier and pickle files of unlabelled glitches and generate the score
file in a .csv file
'''

def main(image_data, model_adr, image_size=[140, 170], verbose=False):
    """
    Parameters
    ----------
    image_data : `pd.DataFrame` this is a DF with
                 columns whose names are the same as
                 the image and whose row entries are
                 the b/w pixel values at some resoltion
                 determined by `read_image`

    model_adr : `str` path to folder containing model

    image_size : `list`, default [140, 170]

    verbose : `boolean`, default False

    Returns
    -------
    """

    dw = label_glitches(pickle_adr, model_adr, image_size, verbose)
    dwslice = dw[0][1:]
    dwslice = numpy.array(map(float, dwslice))

    return dw[0], numpy.argmax(dwslice)


def label_glitches(image_data, model_name, model_type,
                   order_of_channels="channels_last",
                   image_order=['0.5.png', '1.0.png', '2.0.png', '4.0.png'],
                   image_size=[140, 170],
                   verbose=False):
    """Obtain 1XNclasses confidence vector and label for image

    Parameters:

        image_data (`pd.DataFrame`):
            This is a DF with columns whose names are the same as
            the image and whose row entries are
            the b/w pixel values at some resoltion
            determined by `read_image`

        model_name (str):
            Full path to the model

        model_type (str):
            Can be either 'yunan' or 'original'

        image_size (list, optional):
            Default [140, 170]

        verbose (bool, optional):
            Default False

    Returns:

        score3_unlabelled (np.array):
            confidence scores per class (b/t 0 and 1)
            index_label (int): ml label
    """

    numpy.random.seed(1986)  # for reproducibility

    img_rows, img_cols = image_size[0], image_size[1]


    if model_type == "yunan":
        # load a model and weights
        if order_of_channels == 'channels_last':
            reshape_order = (-1, img_rows, img_cols, 3)
        elif order_of_channels == 'channels_first':
            reshape_order = (-1, 3, img_rows, img_cols)
        else:
            raise ValueError("Do not understand supplied channel order")

        final_model = GS_new(23, img_rows, img_cols, 3)
        final_model.load_weights(model_name)

    elif model_type == "original":
        # load a model and weights
        if order_of_channels == 'channels_last':
            reshape_order = (-1, img_rows, img_cols, 1)
        elif order_of_channels == 'channels_first':
            reshape_order = (-1, 1, img_rows, img_cols)
        else:
            raise ValueError("Do not understand supplied channel order")
        final_model = load_model(model_name)
    else:
        raise ValueError("Invalid model_type supplied, must be on of `yunan` or `original`.")

    final_model.compile(loss='categorical_crossentropy',
                        optimizer='adadelta',
                        metrics=['accuracy'])

    first_image_in_panel = sorted(image_data.filter(regex=(image_order[0])).keys())
    second_image_in_panel = sorted(image_data.filter(regex=(image_order[1])).keys())
    third_image_in_panel = sorted(image_data.filter(regex=(image_order[2])).keys())
    fourth_image_in_panel = sorted(image_data.filter(regex=(image_order[3])).keys())
    
    # read in 4 durations
    test_set_unlabelled_x_1 = numpy.vstack(image_data[first_image_in_panel].iloc[0]).reshape(reshape_order)
    test_set_unlabelled_x_2 = numpy.vstack(image_data[second_image_in_panel].iloc[0]).reshape(reshape_order)
    test_set_unlabelled_x_3 = numpy.vstack(image_data[third_image_in_panel].iloc[0]).reshape(reshape_order)
    test_set_unlabelled_x_4 = numpy.vstack(image_data[fourth_image_in_panel].iloc[0]).reshape(reshape_order)

    if model_type == "original":
        concat_test_unlabelled = concatenate_views(test_set_unlabelled_x_1,
                                                   test_set_unlabelled_x_2,
                                                   test_set_unlabelled_x_3,
                                                   test_set_unlabelled_x_4,
                                                   [img_rows, img_cols],
                                                   False,
                                                   order_of_channels)
    elif model_type == "yunan":
        concat_test_unlabelled = {
                "0.5": test_set_unlabelled_x_1,
                "1.0": test_set_unlabelled_x_2,
                "2.0": test_set_unlabelled_x_3,
                "4.0": test_set_unlabelled_x_4,
                }


    confidence_array = final_model.predict(concat_test_unlabelled, verbose=0)
    index_label = confidence_array.argmax(1)

    ids = []
    for uid in first_image_in_panel:
        ids.append(uid.split('_')[1])

    return confidence_array, index_label, ids, first_image_in_panel, second_image_in_panel, third_image_in_panel, fourth_image_in_panel

def get_feature_space(image_data, semantic_model_name, image_size=[140, 170],
                      verbose=False):
    """Obtain N dimensional feature space of sample

    Parameters:

        image_data (`pd.DataFrame`):
            This is a DF with columns whose names are the same as
            the image and whose row entries are
            the b/w pixel values at some resoltion
            determined by `read_image`

        semantic_model_adr (str):
            Path to folder containing similarity model

        image_size (list, optional):
            default [140, 170]

        verbose (bool, optional):
            default False

    Returns:

        np.array:
            a 200 dimensional feature space vector
    """
    img_rows, img_cols = image_size[0], image_size[1]
    semantic_idx_model = load_model(semantic_model_name)
    test_data = image_data.filter(regex=("1.0.png")).iloc[0].iloc[0].reshape(-1, 1, img_rows, img_cols)
    test_data = test_data.reshape([test_data.shape[0], img_rows, img_cols, 1])
    test_data = numpy.repeat(test_data, 3, axis=3)
    new_data2 = []
    for i in test_data:
        new_data2.append(numpy.array(Image.fromarray(i).resize(224, 224)))
        img_cols = 224
        img_rows = 224
        test_data = numpy.asarray(new_data2)

    return semantic_idx_model.predict([test_data])


def get_multiview_feature_space(image_data, semantic_model_name,
                                order_of_channels="channels_last",
                                image_size=[140, 170], verbose=False):
    """Obtain N dimensional feature space of sample

    Parameters:

        image_data (`pd.DataFrame`):
            This is a DF with columns whose names are the same as
            the image and whose row entries are
            the b/w pixel values at some resoltion
            determined by `read_image`

        semantic_model_adr (str):
            Path to folder containing similarity model

        image_size (list, optional):
            default [140, 170]

        verbose (bool, optional):
            default False

    Returns:

        np.array:
            a 200 dimensional feature space vector
    """
    img_rows, img_cols = image_size[0], image_size[1]

    if order_of_channels == 'channels_last':
        reshape_order = (-1, img_rows, img_cols, 3)
    elif order_of_channels == 'channels_first':
        reshape_order = (-1, 3, img_rows, img_cols)
    else:
        raise ValueError("Do not understand supplied channel order")

    half_second_images = sorted(image_data.filter(regex=("0.5.png")).keys())
    one_second_images = sorted(image_data.filter(regex=("1.0.png")).keys())
    two_second_images = sorted(image_data.filter(regex=("2.0.png")).keys())
    four_second_images = sorted(image_data.filter(regex=("4.0.png")).keys())

    test_set_unlabelled_x_1 = numpy.vstack(image_data[half_second_images].iloc[0]).reshape(reshape_order)
    test_set_unlabelled_x_2 = numpy.vstack(image_data[one_second_images].iloc[0]).reshape(reshape_order)
    test_set_unlabelled_x_3 = numpy.vstack(image_data[two_second_images].iloc[0]).reshape(reshape_order)
    test_set_unlabelled_x_4 = numpy.vstack(image_data[four_second_images].iloc[0]).reshape(reshape_order)

    concat_test_unlabelled = concatenate_views(test_set_unlabelled_x_1,
                            test_set_unlabelled_x_2, test_set_unlabelled_x_3, test_set_unlabelled_x_4, [img_rows, img_cols], True, order_of_channels)

    concat_test_unlabelled = preprocess_input(concat_test_unlabelled)

    ids = []
    for uid in half_second_images:
        ids.append(uid.split('_')[1])

    semantic_idx_model = load_model(semantic_model_name)
    features = semantic_idx_model.predict([concat_test_unlabelled])

    return features, ids


def get_deeplayer(image_data, model_name, image_size=[140, 170],
                  verbose=False):
    """Obtain 1XNclasses confidence vector and label for image

    Parameters:

        image_data (`pd.DataFrame`):
            This is a DF with columns whose names are the same as
            the image and whose row entries are
            the b/w pixel values at some resoltion
            determined by `read_image`

        model_adr (str, optional):
            Path to folder containing model

        image_size (list, optional):
            Default [140, 170]

        verbose (bool, optional):
            Default False

    Returns:

        score3_unlabelled (np.array):
            confidence scores per class (b/t 0 and 1)
            index_label (int): ml label
    """

    numpy.random.seed(1986)  # for reproducibility

    img_rows, img_cols = image_size[0], image_size[1]

    # load a model and weights
    if verbose:
        print ('Retrieving the trained ML classifier')
    final_model = load_model(model_name)

    final_model.compile(loss='categorical_crossentropy',
                        optimizer='adadelta',
                        metrics=['accuracy'])

    if verbose:
        print ('Scoring unlabelled glitches')

    half_second_images = sorted(image_data.filter(regex=("0.5.png")).keys())
    one_second_images = sorted(image_data.filter(regex=("1.0.png")).keys())
    two_second_images = sorted(image_data.filter(regex=("2.0.png")).keys())
    four_second_images = sorted(image_data.filter(regex=("4.0.png")).keys())

    # read in 4 durations
    test_set_unlabelled_x_1 = numpy.vstack(image_data[half_second_images].iloc[0].values)
    test_set_unlabelled_x_1 = test_set_unlabelled_x_1.reshape(-1, 1, img_rows, img_cols)

    test_set_unlabelled_x_2 = numpy.vstack(image_data[four_second_images].iloc[0].values)
    test_set_unlabelled_x_2 = test_set_unlabelled_x_2.reshape(-1, 1, img_rows, img_cols)

    test_set_unlabelled_x_3 = numpy.vstack(image_data[one_second_images].iloc[0].values)
    test_set_unlabelled_x_3 = test_set_unlabelled_x_3.reshape(-1, 1, img_rows, img_cols)

    test_set_unlabelled_x_4 = numpy.vstack(image_data[two_second_images].iloc[0].values)
    test_set_unlabelled_x_4 = test_set_unlabelled_x_4.reshape(-1, 1, img_rows, img_cols)

    concat_test_unlabelled = concatenate_views(test_set_unlabelled_x_1,
                            test_set_unlabelled_x_2, test_set_unlabelled_x_3, test_set_unlabelled_x_4, [img_rows, img_cols], False)

    feature_exc1 = K.function([final_model.layers[0].get_input_at(node_index=0),
                K.learning_phase()],
               [final_model.layers[0].get_layer(index=20).output])

    deeplayer = feature_exc1([concat_test_unlabelled, 0])[0]

    ids = []
    for uid in half_second_images:
        ids.append(uid.split('_')[1])

    confidence_array = final_model.predict(concat_test_unlabelled, verbose=0)
    index_label = confidence_array.argmax(1)

    return confidence_array, index_label, deeplayer, ids, half_second_images, one_second_images, two_second_images, four_second_images
