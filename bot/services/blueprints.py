
from endfield.models.factory.blueprint import FactoryPlans , Blueprint , OutputItems
from endfield import Endfield

# items literal used for showing available items
from endfield.factory.factory import items

import json
from pathlib import Path
import endfield

def load_items_dict():
    """
    Load slugs.json from endfield package and create a dict mapping itemId to item info.
    Returns: {itemId: {id, name, icon_url}, ...}
    """
    endfield_path = Path(endfield.__file__).parent
    slugs_file = endfield_path / "assets" /"factory"/ "slugs.json"
    
    with open(slugs_file, 'r', encoding='utf-8') as f:
        slugs_data = json.load(f)
    
    items_dict = {}
    for item_id, slug in slugs_data["itemIdToSlug"].items():
        items_dict[item_id] = {
            "id": item_id,
            "name": slug,
            "icon_url": f"https://endfieldtools.dev/assets/images/endfield/itemicon/{item_id}.png"
        }
    
    return items_dict

ITEMS_INFO = load_items_dict()


async def fetch_blueprint(region: str, item_name: str, page: int = 0):
    """
    Fetch a single blueprint at the specified page
    
    Returns: (blueprint, total_pages) or (None, 0) if not found
    """
    try:
        async with Endfield() as ef:
            bp = await ef.get_factory_blueprints(
                region=region,
                item=item_name,
                start=page,
                end=page+1
            )
        
        if bp.blueprints:
            return bp.blueprints[0], bp.total
        return None, 0
    except Exception as e:
        print(f"Error fetching blueprint: {e}")
        return None, 0


def format_blueprint_caption(blueprint, page: int = 0, total_pages: int = 0) -> str:
    """
    Format blueprint data into a caption string
    
    Args:
        blueprint: Blueprint object from Endfield API
        page: Current page number (0-indexed)
        total_pages: Total number of pages
    
    Returns: Formatted caption string
    """
    outputs = "\n".join(
        f"└➤ {item.name}- {item.per_minute}/min"
        for item in blueprint.output_items
    )
    
    page_info = f"\n\n◆ Page {page + 1}/{total_pages}" if total_pages > 0 else ""
    
    caption = f"""
╭──────────────────╮
│  BLUEPRINT INFO  │
╰──────────────────╯

◆ Name
└➤ {blueprint.name}

◆ Description
└➤ {blueprint.description}

◆ Code
└➤ {blueprint.code}

◆ Region
└➤ {blueprint.region}{page_info}

◆ Output Items
{outputs}
""".strip()
    
    return caption
