"""The one adopter-owned registration file. The engine imports THIS module and
nothing else outside engine/. Add a pack: import it and concatenate/append below.

SECTIONS       list of (slug, title, lede, renderer)  — placed by prose {{section:slug}}
PAGE_PROVIDERS list of callables tok -> [Page]         — whole generated pages
PROVIDER_ORDER {provider.__module__: order}            — interleaves providers with prose
                                                          domains (a domain's order is its <nn>)"""
from engine.packs import glossary, ideas, inbox, config_registry, decisions, designsystem
from packs import example_pack

SECTIONS = (list(designsystem.SECTIONS) + list(example_pack.SECTIONS)
            + list(glossary.SECTIONS) + list(ideas.SECTIONS))
PAGE_PROVIDERS = [config_registry.provider, decisions.provider, inbox.provider]
PROVIDER_ORDER = {
    config_registry.provider.__module__: 5,
    decisions.provider.__module__: 6,
    inbox.provider.__module__: 7,
}
