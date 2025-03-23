from mods_base import CoopSupport, Game, Mod


def get_mod_description(mod: Mod, include_author_version: bool) -> str:
    """
    Gets the full text to use for a mod's description, including the fields we add.

    Args:
        mod: The mod to create the description for.
        include_author_version: If to include the author and version in the header.
    Returns:
        The description text.
    """
    blocks: list[str] = []

    header = ""
    if include_author_version:
        header += f"<font size='14' color='#a1e4ef'>By: {mod.author}\t\t{mod.version}</font>\n"

    match mod.coop_support:
        case CoopSupport.Unknown:
            # Choose this size and colour to make it look the same as the author text above it
            # Can only add one line there, so hiding this at the top of the description
            header += "<font size='14' color='#a1e4ef'>Coop Support: Unknown</font>"
        case CoopSupport.Incompatible:
            header += (
                "<font size='14' color='#a1e4ef'>Coop Support:</font>"
                " <font size='14'color='#ffff00'>Incompatible</font>"
            )
        case CoopSupport.RequiresAllPlayers:
            header += "<font size='14' color='#a1e4ef'>Coop Support: Requires All Players</font>"
        case CoopSupport.ClientSide:
            header += "<font size='14' color='#a1e4ef'>Coop Support: Client Side</font>"
        case CoopSupport.HostOnly:
            header += "<font size='14' color='#a1e4ef'>Coop Support: Host Only</font>"
    blocks.append(header)

    if Game.get_current() not in mod.supported_games:
        supported = [g.name for g in Game if g in mod.supported_games and g.name is not None]
        blocks.append(
            "<font color='#ffff00'>Incompatible Game!</font>\n"
            "This mod supports: " + ", ".join(supported),
        )

    if mod.description:
        blocks.append(mod.description)

    return "\n\n".join(blocks)
