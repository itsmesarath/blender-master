# Render guide

## Engine choice
| Need | Engine |
|---|---|
| realistic product, glass, liquid, interiors | Cycles |
| fast iteration, stylised, motion graphics, real-time look | EEVEE |
| clay or technical previews | Workbench or Cycles with a clay override |
| server or CI without GPU | Cycles CPU |

## Sample budgets (Cycles, adaptive sampling on, denoised)
| Stage | Samples | Resolution |
|---|---|---|
| per-part preview | 8-32 | 480x270 to 960x540 |
| look approval | 64-128 | half of final |
| final still | 256-1024 | full |
| final animation | 128-512 | full; check temporal flicker on a few frames first |

Noise threshold 0.01-0.05 for previews, 0.005-0.01 for finals. Clamp indirect 5-10 removes most
fireflies with little visible change. Light paths: raise transmission bounces for stacked glass.

## Colour management
- View transform **AgX** for natural highlight roll-off; *Standard* only for UI-exact colours
  such as flat logos and motion graphics.
- Looks change contrast (`AgX - Medium High Contrast` etc.). Use exposure for overall
  brightness, light power for balance between parts of the frame.

## Passes worth enabling
| Pass | Use |
|---|---|
| Denoising Albedo / Normal | compositor denoise with better edges |
| Mist | atmospheric depth in the compositor |
| Depth | depth of field or fog in compositing |
| Cryptomatte object/material | masks for grading single objects later |
| Shadow catcher | product shots on any background |

## Compositor recipes (5.x node-group compositor)
- **Denoise**: Render Layers Image + Denoising Albedo + Denoising Normal -> Denoise
  (Prefilter Accurate) -> Group Output.
- **Mist / haze**: Mist pass through a map range into the factor of a mix between the image and
  a haze colour; set mist start and depth in world settings to match the scene scale.
- **Bloom-like glow**: Glare node, type Fog Glow or Bloom, threshold ~1, small strength.
- **Vignette**: an Ellipse Mask, blurred, multiplied over the image at low strength.

## Output
| Delivery | Format |
|---|---|
| web still | PNG 8-bit, or JPEG at the end of the chain |
| print or later grading | PNG 16-bit or EXR |
| keep all passes | OpenEXR multilayer, half float, compressed |
| video | render an image sequence first, encode afterwards (crash-safe) |

## Render checks
- File exists, expected width and height.
- Mean brightness not near zero, not mostly black.
- Alpha present when transparency was requested.
- For sequences: frame count equals the range; spot-check first, middle, last.
