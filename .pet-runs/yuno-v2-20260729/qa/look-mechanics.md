# Yuno Look Mechanics

Yuno is a compact anime-style humanoid pet with large red eyes, pink hair, a pale hoodie, dark skirt or shorts, and black boots. Preserve the exact approved v1 identity, facial proportions, hairstyle, clothing, palette, pixel-adjacent rendering, body scale, and baseline.

## Natural motion

- Keep both boots, lower body, and torso registered to the neutral frame. Do not rotate, skew, stretch, or tilt the whole sprite.
- Let the eyes lead each gaze. Rotate the visible iris and pupil within the original eye construction, reshape the eyelids subtly, and keep highlights and sclera coherent with the eye surface.
- Follow with a small, near-rigid head and neck turn or pitch. Preserve skull, brow, mouth, hoodie, and facial-feature spacing.
- Allow only subtle upper-body follow-through. Hair tufts and side locks may lag by a small, continuous amount; they must not flip sides or change design.
- Keep clothing and limbs attached and stable. Add no props, effects, labels, arrows, shadows, or scenery.
- Each 22.5-degree step should move eyes, eyelids, head angle, and hair by a similar visual amount. Maintain one continuous clockwise loop with no registration jump at 157.5 to 180 or 337.5 to 000.

## Cardinal pose families

- `000 up`: pupils and irises sit visibly above eye center, upper eyelids open toward the gaze, chin lifts slightly, and the top/back hair contour becomes a little more visible. The pose must not read as neutral/front.
- `090 screen-right`: pupils, nose direction, and face turn visibly toward the image's right edge. More of Yuno's screen-left cheek/hair side is visible; the opposite side is slightly occluded.
- `180 down`: pupils and irises sit visibly below eye center, upper eyelids lower slightly, chin tucks, and the forehead/top hair becomes a little more visible. The pose must be distinct from neutral/front.
- `270 screen-left`: pupils, nose direction, and face turn visibly toward the image's left edge. More of Yuno's screen-right cheek/hair side is visible; the opposite side is slightly occluded.

## Diagonals and continuity

Interpolate the cardinal families evenly in viewer coordinates. Rightward diagonals must retain a clear rightward eye/head cue while adding the appropriate vertical cue; leftward diagonals must retain a clear leftward cue. Keep the lower-body anchor, overall height, and apparent volume stable in every cell.
