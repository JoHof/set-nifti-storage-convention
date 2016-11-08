# set-nifti-storage-convention
FSL-tools wrapper for setting a defined storage convention to nifti files.

There are many differnt ways a volumetric image can be stored in a nifti file. Usually, this shouldn't be a problem if the header information is correct as the viewer or processing software can orient the image as desired. However, some tools fail to interpret the header correctly or assume two volumes (e.g. image and annotation volumes in ITK-Snap) to be stored in the same convention. This tool applies the 'fslswapdim' and 'fslorient' tools from the FSL toolbox on an image to change the storage convention. This tool might also help to normalize large heterogenious datasets to a standard convention. Anatomical labels in the header (left, right and so on...) must be set correctly in order to get valid results.

# Example

If you try to load a volume (img.nii.gz) and an annotation (seg.nii.gz) in ITK-Snap and you get the error:
>There is a mismatch between the header of the image that you are loading and the header of the main image currently open in ITK-SNAP. The images have different origin and orientation. ITK-SNAP will ignore the header in the image you are loading.

or 

>Error: Mismatched Dimensions. The size of the segmentation image ... does not match the size of the main image .... Images must have the same dimensions.

The reason might be that the files don't use the same storage convention. If this is the case the segmentation either can't be loaded at all or the appear with wrong orientation.

Try to perform:

```
./set_nifti_sc.py img.nii.gz img.nii.gz
./set_nifti_sc.py seg.nii.gz seg.nii.gz
```

to normalize the images to a standard storage convention.
