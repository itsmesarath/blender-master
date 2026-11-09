# UV and bake guide

## Seam placement
| Asset | Seams |
|---|---|
| box-like prop | around each face group by angle; hide on bottom or back edges |
| cylinder / pipe | one straight seam on the least visible side, caps separate |
| character body | back or side centre line, inner arms, inner legs, around hands and feet |
| head | behind the ears and up the back of the head, under the jaw for close-ups |
| cloth | along real sewing lines (the garment pattern) |

## Densities (px per metre, rough)
| Use | Density |
|---|---|
| first-person hero weapon | 1024-2048 |
| third-person character | 512-1024 |
| environment props | 256-512 |
| distant architecture | 64-256 |

## Bake settings
| Map | Space | Notes |
|---|---|---|
| normal | Non-Color | tangent space, OpenGL (+Y). Unreal wants DirectX (-Y): flip green on export or in the engine |
| ao | Non-Color | 16-64 samples is enough; multiply into base colour or use as an occlusion channel |
| diffuse colour | sRGB | Color pass only (no lighting) |
| roughness / metallic | Non-Color | pack into channels for engines |
| combined | sRGB | lighting baked in; for unlit/mobile or lightmaps |

Cage: start at 1-3% of the object's size; raise if rays miss detail, lower if they hit the
wrong side (thin parts). For very thin parts, use a cage object.

## Channel packing (engine conventions)
- Unreal: ORM (R = occlusion, G = roughness, B = metallic).
- Unity HDRP mask map: R metallic, G occlusion, B detail mask, A smoothness (1 - roughness).
- glTF: occlusion R, roughness G, metallic B.

## UDIMs
For film characters: tiles 1001, 1002... one region per tile (head, body, hands). Bake per
tile by moving islands into the tile range; engines rarely support UDIMs directly.

## Lightmaps
A second UV layer (`uv_name="UVLightmap"`, method `lightmap`), no overlaps, generous margin;
engines import it as the lightmap channel.
