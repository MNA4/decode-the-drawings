# Decode the Drawings Challenge

Radu's "Decode the Drawings" challenge is a fun challenge where you try to reconstruct a drawing by analyzing a video of three colored balls moving in space.

More info can be found here: [Decode the Drawings](https://radufromfinland.com/decodeTheDrawings/)

This project is a solution to Radu's "Decode the Drawings" challenge. It uses computer vision and audio processing to track three colored balls in a video, estimate their 3D positions, compute the orientation of the triangle they form, and infer the pen tip position for drawing. The results are visualized in a custom Pygame UI and optionally saved to a file.

## How it reproduced the drawing

Note: In this project, I'm using the right handed coordinate system for the camera's coordinate system. as shown below:
| Axis |   Direction   | 
|------|---------------|
| +x   | right         |
| +y   | up            |
| +z   | out of camera |
| -z   | into scene    |

The world's coordinate system used in this project is shown below:

*Image 1: World Coordinate System (Credit to Radu for the original image)*

![Image 1: World Coordinate System](https://raw.githubusercontent.com/MNA4/decode-the-drawings/main/images/world_coordinate_system.png)

Here's the program's logic:

1. Get the video frames and audio from the input video.
2. Detect the three colored balls in each frame using color thresholding.
3. For the first frame, we do the following:
    1. Calculate the camera's focal length by comparing the projected distance between each pair of balls and their actual given distances. This allows the program to construct a pinhole camera model.
    
4. For the remaining frames, we do the following:
    1. Calculate the projected center positions & distances of each ball in the image frame.
    2. Calculate rays that point to the center of each ball.
    3. Estimate the distance between the camera and each ball, and use the formula `position = ray * distance` to calculate the position of each ball as viewed from the camera origin.
    4. Calculate the camera's position relative to the average balls position,  in the camera's coordinate system. 
    5. Calculate the pen tip position by subtracting the camera's y-position from the given pen length.
    6. Compute the world's orientation (from the camera's point of view).
    7. Convert the pen tip's coordinates from the camera's coordinate system to the world's coordinate system.
    8. Check if the pen is touching the paper. if it is, save the pen tip coordinates to a list.
5. Add smoothing to the pen tip coordinate to reduce noise.
6. At the end of the video, save the pen tip coordinates to a file.

Here's a more detailed explanation of the steps:

### Step 1: Get Video Frames and Audio

I'm using the `av` library to read the video frames and extract the audio track. The frames are yielded as numpy arrays for further processing.

### Step 2: Threshold the frames

To separate the ball pixels from the background, I apply color thresholding using numpy. I've tried several methods, but currently it uses the following approach:

```py
# threshold value is between 0 and 1

# thresholding the red value
if (r * threshold > (r + g + b) / 3):
    # this pixel is considered a red ball pixel
# thresholding the green value
if (g * threshold > (r + g + b) / 3):
    # this pixel is considered a green ball pixel
# thresholding the blue value
if (b * threshold > (r + g + b) / 3):
    # this pixel is considered a blue ball pixel
```

However, we can optimize this since `r + g + b` and `threshold` value doesn't change for each pixel. We can precompute these values and use them in the thresholding checks:

```py
inv_threshold = 1 / threshold  # precompute the inverse of the threshold
colors = (r,g,b)
avg = sum(colors) * inv_threshold * 0.33333  # precompute the average color value
for i, color in enumerate(colors):
    if color > avg:
        # this pixel is considered a color ball pixel
        # where i is the index of the color (0 for red, 1 for green, 2 for blue)
```

Instead of looping through each pixel and checking the threshold, this project uses numpy's vectorized operations to apply the thresholding in one go. This significantly speeds up the processing time.

**UPDATE:** after reviewing the threshold array, i realized that there are a lot noise coming from low lightness pixels, so I added a lightness threshold to filter out these pixels. The new thresholding algorithm looks like this:

```py
inv_saturation_threshold = 1 / saturation_threshold  # precompute the inverse of the threshold
colors = (r,g,b)
avg = sum(colors) * inv_saturation_threshold * 0.33333  # precompute the average color value
for i, color in enumerate(colors):
    if color > avg and color > lightness_threshold:
        # this pixel is considered a color ball pixel
        # where i is the index of the color (0 for red, 1 for green, 2 for blue)
```



### Step 3.1: Camera Calibration

#### Method 1: use the distance between each ball's centroid
To estimate the camera's focal length, we compare the distance between each pair of balls in the image frame (by calculating their center of mass) with their actual given distances.

This allows the program to construct a pinhole camera model, which is essential for accurately estimating the 3D positions of the balls.

The focal length is calculated using the formula:

source: https://en.wikipedia.org/wiki/Pinhole_camera_model#Formulation

$$
\text{focal length} = \frac{\text{projected length} \times z}{\text{actual length}}
$$

where $\text{projected length}$ is the distance between the projected centers of the balls in the image frame, $z$ is the estimated z-value from the camera to the balls, and $\text{actual length}$ is the actual distance between the balls in the real world.

#### Method 2: using given FOV.

We use the equation:

$$
\text{focal length} = \frac{(w \div 2)}{\tan(\text{horizontal FOV} \ div 2)}
$$

And use the given camera's horizontal FOV.

### Step 4.1-4.2: Calculate Projected Center Positions, Radii, and Rays

This project uses 3 different ways to calculate the ball's projected center & its projected radius from the camera:
#### Method 1: unweighted pixel's average coordinate & area
To approximate the projected center of each ball, we could just calculate the average nonzero pixels' coordinate.

And use the equation $\text{area}=\pi r^2$ to get each ball's projected radii.

However, the ball actually got distorted. which means its actually an ellipse, not a circle. this causes inaccuracy when computing the ball's positions.

##### Calculating the distance between each ball and the camera with given physical & projected radius

We use the following formula to get the z position of the ball with given camera focal length and the ball's physical & projected radius:

source: https://en.wikipedia.org/wiki/Pinhole_camera_model#Formulation

$$
z_i = \frac{\text{focal length} \times \text{actual radius}}{\text{projected radius}}
$$

Where $\text{focal length}$ is the focal length calculated in step 4.1, $\text{actual radius}$ is the physical radius of the ball, and $\text{projected radius}$ is the radius of the ball in the image frame.

And then we use the following formula to get the distance between the camera and the ball:

```
distances[i] = (z[i] / ray[i].z)
```

##### Calculating the rays
To calculate the rays pointing from the camera to the center of each balls, I used the pinhole camera model. The rays are calculated using the formula:

source: https://www.scratchapixel.com/lessons/3d-basic-rendering/ray-tracing-generating-camera-rays/generating-camera-rays.html

```
ray = normalize(vec3(projected_x-principal_x, projected_y-principal_y, f))
```

where `projected_x` and `projected_y` are the x and y coordinates of the projected center of each ball in the image frame, `principal_x` and `principal_y` are the principal point coordinates, and `f` is the focal length calculated in step 4.1.

This gives us a unit vector pointing from the camera to the center of each ball in the image frame (in the camera's coordinate system).
for most cameras, the principal point is at the center of the image, so `principal_x` and `principal_y` are half the width and height of the image respectively.

#### Method 2: ball's tangential point

We know that a sphere projected by a pinhole camera model results in an ellipse pointing towards the principal point. ([Inigo Quilez made an excellent proof here](https://iquilezles.org/articles/sphereproj/))

With this knowledge, we can find 2 points that are tangential to each ball, by calculating the closest & furthest nonzero pixel from the principal point.

We find the angle bisector between the 2 tangential rays. this angle bisector should point directly to the center of each ball. 

This method handles the ellipse distortion pretty well, but it causes too much noise to be useful.

##### Calculating the distance between each ball and the camera with given tangential rays

*Image 2: Tangential Rays*

![Image 2: Tangential Rays](https://raw.githubusercontent.com/MNA4/decode-the-drawings/main/images/tangential_rays.png)

Suppose $\hat{C}$ is the unit ray pointing from the camera to the ball, and $\hat{P}$ is any unit ray tangent to the ball.

$$
\begin{align}
\hat{P} \cdot \hat{C} &= \cos{\theta} = \frac{OP}{OC}, \\
\frac{PC}{OC} &= \sin{\theta} \\
              &= \sqrt{1-\cos^2{\theta}} \\
              &= \sqrt{1-(\hat{P} \cdot \hat{C})^2}, \\
\end{align}
$$

We find:

$$
\text{distance from the camera to the ball} = OC = \frac{PC}{\sqrt{1-(\hat{P} \cdot \hat{C})^2}}
$$ 

Where:

- $PC$ = ball's radius
- $\hat{P}$ = unit tangent ray
- $\hat{C}$ = unit camera‑to‑ball ray

##### Calculating the rays
We can find the angle bisector between 2 rays, by normalizing the sum of the 2 rays:

```
ray = normalize(ray0.x+ray1.x, ray0.y+ray1.y, ray0.z+ray1.z)
```

#### Method 3: weighted pixel's average coordinate & area

To correct the ball’s elliptical distortion, we calculate the weighted average of the pixel positions based on the fraction of the $360\degree × 180\degree$ unit sphere area they occupy.

According to [wikipedia](https://en.wikipedia.org/wiki/Solid_angle):
> The solid angle for an arbitrary oriented surface S subtended at a point P is equal to the solid angle of the projection of the surface S to the unit sphere with center P, which can be calculated as the surface integral:
>
> $$
> \Omega = \iint_S d\Omega = \iint_S \frac{\vec{r} \cdot \hat{n}}{r^3}  dS
> $$
>
> where $\hat{r} = \frac{\vec{r}}{r}$ is the unit vector corresponding to $\vec{r}$, the position vector of an infinitesimal surface element $dS$ with respect to point $P$ and where $\hat{n}$ represents the unit normal vector to $dS$.
>

By substituting $\hat{r} = \frac{\vec{r}}{r},$ we get: 

$$
d\Omega = \frac{\hat{r} \cdot \hat{n}}{r^2} dS = \frac{\vec{r} \cdot \hat{n}}{r^3}dS
$$

In our pinhole‐camera model, $\hat n=(0,0,1)$ and

$$
\vec r = \bigl(x - c_x,y - c_y,f\bigr),
$$

so

$$
\vec r \cdot \hat n = f,
\quad
r = \|\vec r\| = \sqrt{(x - c_x)^2 + (y - c_y)^2 + f^2}.
$$

Putting it all together,

$$
\Omega = \iint_S d \Omega = \iint_S \frac{f}{\bigl((x - c_x)^2 + (y - c_y)^2 + f^2\bigr)^{3/2}}\,dS.
$$

where:

- $\Omega$ = solid angle (in steradians)
- $d\Omega$ = differential solid angle (in steradians)
- $f$ = camera's focal length
- $(c_x, c_y)$ = camera's principal point
- $(x,y)$ = pixel's coordinate
- $dS = 1$ (since each pixel in the image plane corresponds to 1 unit area)

For sufficiently small solid angles $\Omega$, the approximation $\Omega \approx d\Omega$  holds.

To get the pixel's fractional area, we divide solid angle $\Omega$ by a full steradian ($4\pi$):

$$
\text{pixel fractional area} = \frac{\Omega}{4\pi}
$$

And we weight each pixel based on their fractional area to get each ball's projected center:
```py

weights = PIXEL_FRACTIONAL_AREAS

# weighted centroid using np.average
ball_projected_center_x = np.average(ball_x_pixels, weights=weights)
ball_projected_center_y = np.average(ball_y_pixels, weights=weights)
```

**UPDATE:** this isn't the correct way to find the ray's midpoint, since each rays have different length, so we must divide the weights by the ray's length:

```py

weights = PIXEL_FRACTIONAL_AREAS / ray_lengths

# weighted centroid using np.average
ball_projected_center_x = np.average(ball_x_pixels, weights=weights)
ball_projected_center_y = np.average(ball_y_pixels, weights=weights)
```

Now this should give us the mathematically correct center of each ball.

To get the ball’s fractional area, we sum the fractional areas of all nonzero pixels:

$$
\text{ball fractional area} = \sum{\text{pixel fractional area}}
$$

This method handles the ellipse distortion correctly, while still giving minimal noise. this method gives the best results so far.

##### Calculating the distance between each ball and the camera with given fractional area

*Image 3: Spherical cap*

![Image 3: Spherical cap](https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Spherical_cap_diagram.tiff/lossless-page1-597px-Spherical_cap_diagram.tiff.png)

We're gonna find the ball's apparent radius, given its fractional area. 

According to [wikipedia](https://en.wikipedia.org/wiki/Spherical_cap), a sphere cap's surface area can be calculated using the formula:

$$
{A=2\pi r^{2}(1-\cos \theta )}
$$

In a unit sphere, $r = 1$. so:

$$
\begin{align}
A&=2\pi (1-\cos \theta ) \text{ (in steradians)} \\
A&=\frac{1}{2} (1-\cos \theta ) \text{ (in fractional area)}
\end{align}
$$

Solve for $\theta$:

$$
\text{angular radius } \theta = \arccos (1-2A)
$$

We know that $\sin \theta = \frac{PC}{OC}$ (see Image 2), so:

$$
\begin{align}
OC &= \frac{PC}{\sin \theta}  \\
   &= \frac{PC}{\sin (\arccos (1-2A))} \\
   &= \frac{PC}{\sqrt{1 - (1 - 2A)^2}} \\
\end{align}
$$

Where:

- $OC$ = distance between the camera and the ball
- $PC$ = ball's radius
- $A$ = ball's fractional area

##### Calculating the rays

Here, we use the same formula we used in method 1.

### Step 4.3: Distance Estimation
This project uses 2 different methods to estimate the distance between the camera and each ball:

#### Method 1: using law of cosines to calculate the distance between the camera and each ball based on the angles between the rays pointing to each ball (triangulation)

Suppose we have three rays $r_1$, $r_2$, and $r_3$ pointing to the centers of the three balls, distances $t_1$, $t_2$, and $t_3$ such that $r_i t_i$ gives the position of ball $i$ in the camera's coordinate system, and angles $\theta_{12}$, $\theta_{23}$, and $\theta_{31}$ where $\theta_{ij}$ is the angle between rays $r_i$ and $r_j$. We then obtain the following symmetric equations:

$$
\begin{align*}
t_1^2 + t_2^2 - 2 t_1 t_2 \cos\left(\theta_{12}\right) &= s^2 \\
t_2^2 + t_3^2 - 2 t_2 t_3 \cos\left(\theta_{23}\right) &= s^2 \\
t_3^2 + t_1^2 - 2 t_3 t_1 \cos\left(\theta_{31}\right) &= s^2
\end{align*}
$$

where $s$ is the distance between each pair of balls in the real world.

We can solve these equations for $t_1$, $t_2$, and $t_3$, and obtain the following equations (I used AI with this part):

$$
\begin{aligned}
t_1 &= \frac{s\,(1 - r_2\cdot r_3)}{\sqrt{\,2\,(1 - r_1\cdot r_2)\,(1 - r_2\cdot r_3)\,(1 - r_3\cdot r_1)\,}},\\
t_2 &= \frac{s\,(1 - r_1\cdot r_3)}{\sqrt{\,2\,(1 - r_1\cdot r_2)\,(1 - r_2\cdot r_3)\,(1 - r_3\cdot r_1)\,}},\\
t_3 &= \frac{s\,(1 - r_1\cdot r_2)}{\sqrt{\,2\,(1 - r_1\cdot r_2)\,(1 - r_2\cdot r_3)\,(1 - r_3\cdot r_1)\,}}.
\end{aligned}
$$

We can find the real world position of each ball by multiplying the ray by the distance:

```
positions[i] = rays[i] * t[i]
```

#### Method 2: Using the distance we computed in step 3 (trilateration)

Again, here we use the formula

```
positions[i] = rays[i] * distances[i]
```

And calculate the distance using the formula we just solved in step 4.1-4.2.

**for step 4.4-4.5, nothing interesting happens, we just calculate the camera's position relative to the average balls position, and then we find the pen tip position in the camera's coordinate system.**

### Step 4.6: Computing the world's orientation from the camera's point of view
We know that the line formed by the green ball and the blue ball is parallel to the x-axis in the world's coordinate system (see Image 1). So we can use the vector from the green ball to the blue ball to compute the world's x-axis direction.

To compute the z-axis, we cross the x-axis direction with the vector from the red ball to the blue ball.

Finally, we compute the y-axis direction by crossing the z-axis with the x-axis.

### Step 4.6: Convert Pen Tip Coordinates to World Coordinate System
We use the following formula to convert the pen tip coordinates from the camera's coordinate system to the world's coordinate system:

source: https://en.wikipedia.org/wiki/Euclidean_vector#Conversion_between_multiple_Cartesian_bases

$$
x' = \text{x axis} \cdot \text{pos}
$$
$$
y' = \text{y axis} \cdot \text{pos}
$$
$$
z' = \text{z axis} \cdot \text{pos}
$$

where $x'$, $y'$, and $z'$ are the pen tip coordinates in the world's coordinate system, and $\text{pos}$ are the pen tip coordinates in the camera's coordinate system.

### Step 4.7: Check if the Pen is Touching the Paper
This project uses 2 different methods to check if the pen is touching the paper:
#### Method 1: Using the Pen Length
If the pen tip's y-coordinate in the world's coordinate system is less than or equal to the negative of the pen length (plus a threshold), then the pen is touching the paper.
#### Method 2: Using audio intensity
If the audio intensity is above a certain threshold, then the pen is touching the paper. This method is more robust, as it can detect the pen touching the paper even if the pen tip's y-coordinate is above the negative of the pen length. The audio intensity is calculated using the following formula:
```
audio_intensity = rms(audio_samples)
```
where `rms` is the root mean square of the audio samples, `audio_samples` is a list of audio samples from the audio track of the video, and `max_amplitude` is the maximum amplitude of the audio samples, and `audio_samples` is a list of audio samples from the audio track of the video.

### Step 5: Smoothing the recovered image

For now, we just calculate the median of the points every n points, where n is the smoothing constant.

## Requirements
- Python 3.8+
- numpy
- pygame

Install dependencies with:
```
pip install -r requirements.txt
```

## Usage
1. Place your input video (e.g., `3.mp4`) in `./videos`.
2. Adjust configuration parameters in `script.py` if needed (e.g., `VIDEO_PATH`, `PIXEL_THRESHOLD`, etc).
   1. 
3. Run the main script:
```
python script.py
```

### Setting the constants

#### 1. Input & Output files

the `QUEUE` constant must contain a list of dictionaries in the following format:

```py
{
    'input': video_input_path,
    'output': image_output_path
}
```

#### 2. Ellipse Correction method

Set one or less of these constants to True:
- `TANGENTIAL_ELLIPSE_CORRECTION`
- `WEIGHTED_PIXELS_ELLIPSE_CORRECTION`

If you use `TANGENTIAL_ELLIPSE_CORRECTION`, you have the option to use a line mask, `USE_LINE_MASK = True` (i originally added the line mask option cause i thought it would reduce the noise? but it somehow increased the noise)

#### 3. Pen Down Detection Method

set `IGNORE_AUDIO` to False if you want to use audio for detecting pen downs.

if you set `IGNORE_AUDIO` to False, use `AUDIO_THRESHOLD` to adjust the pen down threshold.

Otherwise use `PEN_THRESHOLD` to adjust the pen threshold.

#### 4. Distance Calculation Method

set `IGNORE_BALL_RADIUS` to True if you want to use only angles to calculate distances.

#### 5. Frame Thresholding

- `PIXEL_SATURATION_THRESHOLD` is the saturation threshold. 100 means 100% saturated. setting this to zero will cause zero division error.
- `PIXEL_LIGHTNESS_THRESHOLD` is the lightness threshold. 255 means pure white.

#### 6. Smoothing Constant

adjust `SMOOTHING_CONSTANT` to set how smooth you want the path to be, minimum values is 1 (1 means no smoothing)

#### 7. App Settings

set `PADDING` to the desired UI padding.

set the `FPS` to something low, if you want low CPU load.

set `DEBUG_BALLS` to True, to see the difference between the reconstructed & the real balls.

set `SKIP_FRAMES` to something larger than 1 to render quick preview.

#### 8. Setup Dimensions

Don't change this, unless you used a different setup dimensions.

#### 9. Camera Constants

This is used to calibrate the camera's focal length.

set the `CAM_HORIZONTAL_FOV` to None, if you want the program to calibrate focal length automatically. otherwise it will use the equation `focal = (resolution / 2) / (tan(fov) / 2)`

`DST_CALIB_CONSTANT` is used to fine tune the distortion in the image.

## File Overview
- `script.py` — Main application logic and UI
- `widgets.py` — Custom Pygame UI toolkit
- `image_processing.py` — Ball detection and image utilities
- `media.py` — Video and audio input utilities
- `ball_vectors.py` — 3D geometry and math utilities
- `requirements.txt` — Python dependencies

## Notes
- No OpenCV is required; all image processing is done with numpy and pygame.
- For best results, use a video with clear, well-separated colored balls and minimal background clutter.

## TODO
- [x] Improve ball detection using more robust methods (e.g., ellipse fitting).
- [ ] Allow user to change parameters via UI.
- [ ] Use neural network to correct error in pen tip coordinates.
## License
Copyright (c) 2025 https://github.com/MNA4

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.