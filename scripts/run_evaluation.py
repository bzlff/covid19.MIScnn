#==============================================================================#
#  Author:       Dominik Müller                                                #
#  Copyright:    2020 IT-Infrastructure for Translational Medical Research,    #
#                University of Augsburg                                        #
#                                                                              #
#  This program is free software: you can redistribute it and/or modify        #
#  it under the terms of the GNU General Public License as published by        #
#  the Free Software Foundation, either version 3 of the License, or           #
#  (at your option) any later version.                                         #
#                                                                              #
#  This program is distributed in the hope that it will be useful,             #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of              #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
#  GNU General Public License for more details.                                #
#                                                                              #
#  You should have received a copy of the GNU General Public License           #
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#==============================================================================#
#-----------------------------------------------------#
#                   Library imports                   #
#-----------------------------------------------------#
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import os
from miscnn.data_loading.interfaces import NIFTI_interface
from miscnn import Data_IO

#-----------------------------------------------------#
#                    Visualization                    #
#-----------------------------------------------------#
def visualize_evaluation(case_id, vol, truth, pred, eva_path):
    # Squeeze image files to remove channel axis
    vol = np.squeeze(vol, axis=-1)
    truth = np.squeeze(truth, axis=-1)
    pred = np.squeeze(pred, axis=-1)
    # Color volumes according to truth and pred segmentation
    vol_truth = overlay_segmentation(vol, truth)
    vol_pred = overlay_segmentation(vol, pred)
    # Create a figure and two axes objects from matplot
    fig, (ax1, ax2) = plt.subplots(1, 2)
    # Initialize the two subplots (axes) with an empty image
    data = np.zeros(vol.shape[0:2])
    ax1.set_title("Ground Truth")
    ax2.set_title("Prediction")
    img1 = ax1.imshow(data)
    img2 = ax2.imshow(data)
    # Update function for both images to show the slice for the current frame
    def update(i):
        plt.suptitle("Case ID: " + str(case_id) + " - " + "Slice: " + str(i))
        img1.set_data(vol_truth[:,:,i])
        img2.set_data(vol_pred[:,:,i])
        return [img1, img2]
    # Compute the animation (gif)
    ani = animation.FuncAnimation(fig, update, frames=truth.shape[2],
                                  interval=10, repeat_delay=0, blit=False)
    # Set up the output path for the gif
    if not os.path.exists(eva_path):
        os.mkdir(eva_path)
    file_name = "visualization." + str(case_id).zfill(5) + ".gif"
    out_path = os.path.join(eva_path, file_name)
    # Save the animation (gif)
    ani.save(out_path, writer='imagemagick', fps=20)
    # Close the matplot
    plt.close()

# Based on: https://github.com/neheller/kits19/blob/master/starter_code/visualize.py
def overlay_segmentation(vol, seg):
    # Scale volume to greyscale range
    vol_scaled = (vol - np.min(vol)) / (np.max(vol) - np.min(vol))
    vol_greyscale = np.around(vol_scaled * 255, decimals=0).astype(np.uint8)
    # Convert volume to RGB
    vol_rgb = np.stack([vol_greyscale, vol_greyscale, vol_greyscale], axis=-1)
    # Initialize segmentation in RGB
    shp = seg.shape
    seg_rgb = np.zeros((shp[0], shp[1], shp[2], 3), dtype=np.int)
    # Set class to appropriate color
    seg_rgb[np.equal(seg, 1)] = [0, 0, 255]
    seg_rgb[np.equal(seg, 2)] = [0, 0, 255]
    seg_rgb[np.equal(seg, 3)] = [255, 0, 0]
    # Get binary array for places where an ROI lives
    segbin = np.greater(seg, 0)
    repeated_segbin = np.stack((segbin, segbin, segbin), axis=-1)
    # Weighted sum where there's a value to overlay
    alpha = 0.3
    vol_overlayed = np.where(
        repeated_segbin,
        np.round(alpha*seg_rgb+(1-alpha)*vol_rgb).astype(np.uint8),
        np.round(vol_rgb).astype(np.uint8)
    )
    # Return final volume with segmentation overlay
    return vol_overlayed

#-----------------------------------------------------#
#                  Score Calculations                 #
#-----------------------------------------------------#
def calc_DSC(truth, pred, classes):
    dice_scores = []
    # Iterate over each class
    for i in range(classes):
        try:
            gt = np.equal(truth, i)
            pd = np.equal(pred, i)
            # Calculate Dice
            dice = 2*np.logical_and(pd, gt).sum() / (pd.sum() + gt.sum())
            dice_scores.append(dice)
        except ZeroDivisionError:
            dice_scores.append(0.0)
    # Return computed Dice Similarity Coefficients
    return dice_scores

def calc_Sensitivity(truth, pred, classes):
    sens_scores = []
    # Iterate over each class
    for i in range(classes):
        try:
            gt = np.equal(truth, i)
            pd = np.equal(pred, i)
            # Calculate sensitivity
            sens = np.logical_and(pd, gt).sum() / gt.sum()
            sens_scores.append(sens)
        except ZeroDivisionError:
            sens_scores.append(0.0)
    # Return computed sensitivity scores
    return sens_scores

def calc_Specificity(truth, pred, classes):
    spec_scores = []
    # Iterate over each class
    for i in range(classes):
        try:
            not_gt = np.logical_not(np.equal(truth, i))
            not_pd = np.logical_not(np.equal(pred, i))
            # Calculate specificity
            spec = np.logical_and(not_pd, not_gt).sum() / (not_gt).sum()
            spec_scores.append(spec)
        except ZeroDivisionError:
            spec_scores.append(0.0)
    # Return computed specificity scores
    return spec_scores

#-----------------------------------------------------#
#                      Plotting                       #
#-----------------------------------------------------#

#-----------------------------------------------------#
#                    Run Evaluation                   #
#-----------------------------------------------------#
# Initialize Data IO Interface for NIfTI data
## We are using 4 classes due to [background, lung_left, lung_right, covid-19]
interface = NIFTI_interface(channels=1, classes=4)

# Create Data IO object to load and write samples in the file structure
data_io = Data_IO(interface, input_path="data", output_path="predictions")

# Access all available samples in our file structure
sample_list = data_io.get_indiceslist()
sample_list.sort()

# Iterate over each sample
for index in sample_list:
    # Load a sample including its image, ground truth and prediction
    sample = data_io.sample_loader(index, load_seg=True, load_pred=True)
    # Access image, ground truth and prediction data
    image = sample.img_data
    truth = sample.seg_data
    pred = sample.pred_data
    # Compute diverse Scores
    dsc = calc_DSC(truth, pred, classes=4)
    print(dsc)
    sens = calc_Sensitivity(truth, pred, classes=4)
    print(sens)
    specs = calc_Specificity(truth, pred, classes=4)
    print(specs)
    # Compute Visualization
    #visualize_evaluation(index, image, truth, pred, "evaluation/visualization")

    break
