# app/services/disease_info.py
#
# Reference information for the 38 PlantVillage classes the trained classifier
# can output. This is static agronomic content compiled from public extension
# and plant-pathology resources (see SOURCES); it is NOT produced by the model
# and must never be presented as an image-level diagnosis.
#
# Only fields that are genuinely known are stored: category, causal agent
# (where it is unambiguous), overview, visible symptoms and general management.
# No severity scores, affected-area estimates, box coordinates, expected
# efficacy or cure claims — the classifier provides none of those.
from __future__ import annotations

SOURCES = [
    {
        "name": "Penn State Extension — Plant Disease Fact Sheets",
        "url": "https://extension.psu.edu/plant-diseases",
    },
    {
        "name": "Cornell Plant Disease Diagnostic Clinic",
        "url": "https://plantclinic.cornell.edu/",
    },
    {
        "name": "UC IPM — Pest Management Guidelines",
        "url": "https://ipm.ucanr.edu/",
    },
    {
        "name": "University of Minnesota Extension — Plant Diseases",
        "url": "https://extension.umn.edu/plant-diseases",
    },
]

GUIDANCE_NOTE = (
    "General crop-disease guidance compiled from public extension resources. "
    "It describes the named disease in general, not this specific photo, and "
    "is not a treatment recommendation. Confirm with your local extension "
    "service before applying any control measure."
)

CATEGORY_LABELS = {
    "fungal": "Fungal disease",
    "oomycete": "Oomycete disease",
    "bacterial": "Bacterial disease",
    "viral": "Viral disease",
    "pest": "Arthropod pest",
    "healthy": "Healthy plant",
    "unknown": "Unclassified",
}


def _entry(category, agent, overview, symptoms, management):
    return {
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "agent": agent,
        "overview": overview,
        "symptoms": symptoms,
        "management": management,
    }


DISEASE_INFO = {
    "Apple___Apple_scab": _entry(
        "fungal", "Venturia inaequalis",
        "A common apple disease of cool, wet spring weather that damages leaves and fruit and can reduce yield in wet seasons.",
        [
            "Olive-green to black velvety spots on leaves, often near the veins",
            "Spots later turn brown and the surrounding leaf tissue yellows",
            "Dark, scabby, corky lesions on fruit that may crack",
        ],
        [
            "Choose scab-resistant cultivars where available",
            "Rake up and destroy fallen leaves to reduce overwintering inoculum",
            "Prune to open the canopy so leaves dry faster",
            "Apply protectant fungicides on a program timed to wet spring weather, following the label",
        ],
    ),
    "Apple___Black_rot": _entry(
        "fungal", "Botryosphaeria obtusa",
        "A fruit-rot and canker disease that also causes distinctive leaf spots; it is favoured by warm, wet weather and winter-injured wood.",
        [
            "Small purple-brown 'frogeye' leaf spots with lighter centres",
            "Firm brown fruit rot, often with concentric rings and black specks",
            "Sunken bark cankers and dieback on branches",
        ],
        [
            "Remove mummified fruit and dead wood from the tree and the ground",
            "Prune out cankers during dry weather, disinfecting tools between cuts",
            "Maintain tree vigour; avoid wounding and winter injury",
            "Use labelled fungicides during the growing season where the disease is established",
        ],
    ),
    "Apple___Cedar_apple_rust": _entry(
        "fungal", "Gymnosporangium juniperi-virginianae",
        "A rust that needs both apple and a juniper/cedar host to complete its life cycle, so disease pressure depends on nearby evergreens.",
        [
            "Bright yellow-orange spots on the upper leaf surface in spring",
            "Raised orange lesions with tube-like structures on the leaf underside",
            "Spotting and deformation of fruit in severe cases",
        ],
        [
            "Where practical, remove nearby juniper/cedar hosts within a few hundred metres",
            "Plant rust-resistant apple cultivars",
            "Apply protectant fungicides during the spring infection window if pressure is high",
        ],
    ),
    "Cherry_(including_sour)___Powdery_mildew": _entry(
        "fungal", "Podosphaera clandestina",
        "A surface mildew that develops on young leaves and shoots, typically in warm weather with high humidity but little free water.",
        [
            "White, powdery patches on young leaves and shoot tips",
            "Leaves may curl, pucker or become distorted",
            "Powdery growth can spread to fruit stems in severe cases",
        ],
        [
            "Prune to improve air movement and light penetration",
            "Avoid excessive nitrogen, which promotes dense susceptible growth",
            "Apply labelled mildew fungicides when first colonies appear",
        ],
    ),
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": _entry(
        "fungal", "Cercospora zeae-maydis",
        "A residue-borne leaf spot that becomes important where corn follows corn and summers are humid; it reduces photosynthetic area late in the season.",
        [
            "Long, narrow rectangular lesions with straight edges between veins",
            "Lesions start tan to grey-green and mature to grey or tan",
            "Heavy infection can blight whole leaves before grain fill",
        ],
        [
            "Rotate away from corn for one to two years",
            "Use tillage or residue management to reduce surface inoculum",
            "Plant hybrids with good grey-leaf-spot tolerance",
            "Fungicide application is most useful when lesions appear before tasselling; follow local guidance",
        ],
    ),
    "Corn_(maize)___Common_rust_": _entry(
        "fungal", "Puccinia sorghi",
        "A rust spread by wind-borne spores that is favoured by cool, humid conditions and usually appears on leaves before tasselling.",
        [
            "Small reddish-brown pustules on both leaf surfaces",
            "Pustules rupture the leaf surface and release powdery spores",
            "Severe infections yellow and dry the leaf early",
        ],
        [
            "Plant rust-tolerant hybrids",
            "Avoid very late planting where rust arrives early in the season",
            "Fungicides are rarely economic unless infection starts early on susceptible hybrids",
        ],
    ),
    "Corn_(maize)___Northern_Leaf_Blight": _entry(
        "fungal", "Exserohilum turcicum",
        "A residue-borne blight that spreads in moderate temperatures with long dew periods and can cause substantial leaf loss on susceptible hybrids.",
        [
            "Long, cigar-shaped grey-green to tan lesions",
            "Lesions enlarge and merge, blighting large leaf areas",
            "Damage often starts on lower leaves and moves upward",
        ],
        [
            "Rotate crops and manage residue",
            "Choose hybrids with northern-leaf-blight resistance",
            "Apply fungicides when lesions appear before or around tasselling on susceptible hybrids",
        ],
    ),
    "Grape___Black_rot": _entry(
        "fungal", "Guignardia bidwellii",
        "A disease of warm, wet growing seasons that attacks leaves and destroys fruit; mummified berries carry the fungus over winter.",
        [
            "Tan leaf spots with dark brown margins and tiny black dots in the centre",
            "Berries soften, turn brown-black and shrivel into hard mummies",
            "Black lesions on shoots and tendrils",
        ],
        [
            "Remove and destroy mummified berries and infected canes",
            "Keep the canopy open and weed-free to speed drying",
            "Apply labelled fungicides from early shoot growth through fruit set in wet seasons",
        ],
    ),
    "Grape___Esca_(Black_Measles)": _entry(
        "fungal", "A complex of wood-infecting fungi (e.g. Phaeomoniella, Phaeoacremonium)",
        "A trunk-disease complex of mature vines that plugs water-conducting tissue and causes sudden leaf scorch; it develops over years and has no curative treatment.",
        [
            "Interveinal yellowing or reddening in stripes ('tiger stripes')",
            "Sudden leaf scorch and dieback of shoots or whole arms",
            "Dark streaking in the wood and small dark spots on berries",
        ],
        [
            "Use clean, certified planting material",
            "Prune late in dry weather and seal large cuts",
            "Remove severely affected vines and avoid reusing contaminated pruning tools",
        ],
    ),
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": _entry(
        "fungal", "Pseudocercospora (Isariopsis) clavispora",
        "A late-season leaf spot of humid climates that can cause premature defoliation and weaken vines over successive years.",
        [
            "Irregular brown lesions, often angular and limited by veins",
            "Lesions may have a darker margin with a lighter centre",
            "Severe spotting leads to early leaf drop",
        ],
        [
            "Improve canopy airflow and avoid overhead irrigation",
            "Remove infected leaf litter after harvest",
            "Use labelled fungicides where the disease recurs each season",
        ],
    ),
    "Orange___Haunglongbing_(Citrus_greening)": _entry(
        "bacterial", "Candidatus Liberibacter asiaticus (spread by the Asian citrus psyllid)",
        "A systemic, incurable bacterial disease of citrus spread by a psyllid vector; infected trees decline over years and there is no cure.",
        [
            "Blotchy, asymmetric yellow mottle that crosses leaf veins",
            "Lopsided, small fruit that stays green at the bottom and tastes bitter",
            "Twig dieback, sparse canopy and slow decline",
        ],
        [
            "Use certified disease-free nursery stock",
            "Control the psyllid vector with scouting and recommended insecticide programs",
            "Remove confirmed infected trees to protect surrounding groves",
            "Report suspected cases to the local plant-health authority",
        ],
    ),
    "Peach___Bacterial_spot": _entry(
        "bacterial", "Xanthomonas arboricola pv. pruni",
        "A bacterial disease favoured by warm, wet spring weather that blemishes fruit and can cause heavy leaf loss on susceptible cultivars.",
        [
            "Small water-soaked spots that turn purple-brown and angular",
            "Spots drop out, leaving a shot-hole appearance",
            "Sunken dark pits and gumming on fruit",
        ],
        [
            "Plant resistant cultivars and avoid highly susceptible ones",
            "Prune and fertilise to maintain vigour without excess nitrogen",
            "Avoid overhead irrigation and working in wet foliage",
        ],
    ),
    "Pepper,_bell___Bacterial_spot": _entry(
        "bacterial", "Xanthomonas spp. (e.g. X. euvesicatoria)",
        "A seed- and debris-borne bacterial disease that spreads in warm, wet weather and defoliates plants, exposing fruit to sunscald.",
        [
            "Small water-soaked spots that turn brown with yellow halos",
            "Spots on leaves, stems and fruit; leaves may drop early",
            "Raised, scabby lesions on fruit",
        ],
        [
            "Use certified pathogen-free seed and transplants",
            "Rotate away from peppers and tomatoes for at least two years",
            "Avoid overhead irrigation and handling wet plants",
            "Copper-based sprays may slow spread when started early; follow local guidance",
        ],
    ),
    "Potato___Early_blight": _entry(
        "fungal", "Alternaria solani",
        "A common disease of ageing potato foliage that starts on lower leaves and can reduce tuber bulking when it defoliates plants early.",
        [
            "Dark brown spots with concentric rings ('target' pattern)",
            "Yellowing around lesions, usually on older lower leaves first",
            "Lesions merge and the leaf dries and drops",
        ],
        [
            "Rotate away from potato and tomato for two to three years",
            "Maintain balanced nutrition and adequate irrigation to limit plant stress",
            "Apply labelled fungicides once lesions are found on lower leaves",
        ],
    ),
    "Potato___Late_blight": _entry(
        "oomycete", "Phytophthora infestans",
        "A destructive, fast-moving disease of cool, wet weather that can destroy foliage within days and rot tubers; historically the cause of the Irish potato famine.",
        [
            "Water-soaked, grey-green lesions that enlarge quickly",
            "A white fuzzy mould on the leaf underside in humid conditions",
            "Whole plants collapse and tubers develop reddish-brown rot",
        ],
        [
            "Plant certified seed and resistant varieties where available",
            "Destroy cull piles and volunteer plants that harbour the pathogen",
            "Apply protectant fungicides before extended wet periods; follow regional blight warnings",
            "Harvest in dry conditions and avoid tuber wounding",
        ],
    ),
    "Squash___Powdery_mildew": _entry(
        "fungal", "Podosphaera xanthii",
        "A surface mildew that spreads in warm days with cool nights and can strip photosynthetic area from cucurbit leaves late in the season.",
        [
            "White powdery spots on the upper leaf surface",
            "Patches merge and leaves yellow, brown and dry",
            "Stems and older leaves affected first in dense plantings",
        ],
        [
            "Plant resistant varieties and space plants for airflow",
            "Avoid excess nitrogen and overhead watering",
            "Apply labelled fungicides or biofungicides at first sign, rotating modes of action",
        ],
    ),
    "Strawberry___Leaf_scorch": _entry(
        "fungal", "Diplocarpon earlianum",
        "A leaf-spot disease that builds up in warm, wet weather and reduces vigour when extensive spotting causes early leaf death.",
        [
            "Small purple to dark-red spots that enlarge and merge",
            "Leaf margins and tips dry and look scorched",
            "Severely affected leaves turn brown and die",
        ],
        [
            "Renovate plantings and remove old infected leaves",
            "Improve airflow and avoid overhead irrigation",
            "Rotate beds and use clean transplants",
            "Apply labelled fungicides during wet periods where the disease recurs",
        ],
    ),
    "Tomato___Bacterial_spot": _entry(
        "bacterial", "Xanthomonas spp.",
        "A seed- and debris-borne bacterial disease that spreads with rain splash and handling, defoliating plants in warm, wet weather.",
        [
            "Small dark water-soaked spots with yellow halos",
            "Spots on leaves, stems and green fruit",
            "Heavy spotting causes leaf drop and sunscald of fruit",
        ],
        [
            "Use certified pathogen-free seed and transplants",
            "Rotate away from tomato and pepper for at least two years",
            "Avoid overhead irrigation and working among wet plants",
            "Copper-based sprays may reduce spread when applied early; follow local guidance",
        ],
    ),
    "Tomato___Early_blight": _entry(
        "fungal", "Alternaria solani",
        "A common foliar disease that typically begins on older lower leaves and progresses upward, becoming more severe on stressed plants.",
        [
            "Brown lesions with concentric rings on older leaves",
            "Yellow halos around lesions and progressive yellowing",
            "Dark sunken lesions at the stem base and on fruit",
        ],
        [
            "Rotate with non-solanaceous crops for two to three years",
            "Mulch to reduce soil splash and stake plants for airflow",
            "Remove infected lower leaves and destroy debris",
            "Apply labelled fungicides on a preventive schedule when conditions favour disease",
        ],
    ),
    "Tomato___Late_blight": _entry(
        "oomycete", "Phytophthora infestans",
        "A rapidly spreading disease of cool, humid weather that can destroy a planting within days; the same pathogen causes potato late blight.",
        [
            "Large, greasy grey-green to brown lesions on leaves and stems",
            "White fuzzy growth on the underside in damp weather",
            "Firm brown rot on fruit and rapid plant collapse",
        ],
        [
            "Avoid overhead irrigation and work only in dry foliage",
            "Remove and destroy infected plants promptly; do not compost them",
            "Keep potato and tomato plantings separated",
            "Apply protectant fungicides ahead of wet weather; follow regional warning systems",
        ],
    ),
    "Tomato___Leaf_Mold": _entry(
        "fungal", "Passalora fulva",
        "A disease most severe in humid greenhouses and tunnels where air movement is poor and leaves stay wet.",
        [
            "Pale green to yellow patches on the upper leaf surface",
            "Olive-green to brown velvety mould on the corresponding underside",
            "Leaves curl, brown and drop in severe cases",
        ],
        [
            "Increase ventilation and reduce humidity in tunnels and greenhouses",
            "Space and prune plants to improve airflow",
            "Water at the base and avoid wetting foliage",
            "Use labelled fungicides where the disease recurs",
        ],
    ),
    "Tomato___Septoria_leaf_spot": _entry(
        "fungal", "Septoria lycopersici",
        "A splash-dispersed leaf spot that starts on lower leaves after wet weather and causes steady defoliation through the season.",
        [
            "Many small circular spots with grey centres and dark margins",
            "Tiny black specks (spore bodies) visible inside older spots",
            "Lower leaves yellow and drop, exposing fruit to sunscald",
        ],
        [
            "Rotate away from tomato and remove crop debris",
            "Mulch to limit soil splash and stake plants",
            "Remove infected lower leaves early",
            "Apply labelled fungicides preventively during wet periods",
        ],
    ),
    "Tomato___Spider_mites Two-spotted_spider_mite": _entry(
        "pest", "Tetranychus urticae (two-spotted spider mite)",
        "A sap-feeding mite, not a pathogen; populations build in hot, dry conditions and can defoliate plants quickly.",
        [
            "Fine pale speckling or stippling on the upper leaf surface",
            "Bronzing or yellowing of leaves, often starting near veins",
            "Fine webbing on leaf undersides in heavy infestations",
        ],
        [
            "Check leaf undersides regularly, especially in hot dry spells",
            "Keep plants adequately watered; drought stress favours mites",
            "Conserve or release predatory mites where compatible",
            "Use labelled miticides if thresholds are exceeded, rotating modes of action",
        ],
    ),
    "Tomato___Target_Spot": _entry(
        "fungal", "Corynespora cassiicola",
        "A warm, humid-weather leaf spot that also damages fruit and stems, often appearing after periods of high rainfall.",
        [
            "Brown lesions with concentric rings and a yellow halo",
            "Spots on leaves, stems and fruit",
            "Premature defoliation in severe epidemics",
        ],
        [
            "Rotate crops and bury or remove residue",
            "Improve airflow and avoid overhead irrigation",
            "Apply labelled fungicides when conditions favour disease",
        ],
    ),
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": _entry(
        "viral", "Tomato yellow leaf curl virus (transmitted by whitefly)",
        "A whitefly-transmitted virus with no cure; control depends on managing the vector and preventing introduction.",
        [
            "Upward curling and cupping of young leaves",
            "Yellowing of leaf margins and interveinal tissue",
            "Stunted plants with few, small fruit",
        ],
        [
            "Use virus-free transplants and resistant varieties where available",
            "Control whiteflies with screening, yellow sticky traps and recommended insecticides",
            "Remove and destroy infected plants",
            "Keep weed hosts around the crop under control",
        ],
    ),
    "Tomato___Tomato_mosaic_virus": _entry(
        "viral", "Tobacco mosaic virus",
        "A highly stable virus spread mainly by handling and contaminated tools and seed; it has no cure and persists in debris and on surfaces.",
        [
            "Light and dark green mosaic mottling of leaves",
            "Leaf distortion, narrowing or 'fern-leaf' growth",
            "Stunted plants with uneven ripening",
        ],
        [
            "Use certified virus-free seed and resistant varieties",
            "Wash hands and disinfect tools; do not smoke or handle tobacco near plants",
            "Remove and destroy infected plants",
            "Avoid saving seed from affected crops",
        ],
    ),
}

HEALTHY_INFO = {
    "category": "healthy",
    "category_label": CATEGORY_LABELS["healthy"],
    "agent": None,
    "overview": (
        "The model's best match for this image is a class labelled healthy: no "
        "disease symptom is represented by that class in the training data."
    ),
    "symptoms": [],
    "management": [
        "Continue routine scouting, especially after rain or irrigation",
        "Keep the canopy open and irrigate at the base to limit leaf wetness",
        "Photograph any new lesions and rescan for a second opinion",
    ],
}


def get_disease_info(class_name: str | None) -> dict | None:
    """Static reference entry for a checkpoint class name, if one exists."""
    if not class_name:
        return None
    if class_name in DISEASE_INFO:
        entry = dict(DISEASE_INFO[class_name])
    elif class_name.endswith("___healthy"):
        entry = dict(HEALTHY_INFO)
    else:
        return None
    entry["guidance_note"] = GUIDANCE_NOTE
    entry["sources"] = SOURCES
    return entry


def get_category(class_name: str | None) -> dict:
    """Category of a checkpoint class: label plus stable machine key."""
    entry = get_disease_info(class_name)
    if entry is None:
        return {"key": "unknown", "label": CATEGORY_LABELS["unknown"]}
    return {"key": entry["category"], "label": entry["category_label"]}
