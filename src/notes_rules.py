"""Reference labeller built from the AGENT'S CLOSING NOTE.

Not usable in production (notes do not exist when the ticket is created) but they are a
strong independent 'answer key' for checking the LLM, which only sees the customer message.
Returns None when the note has no clear topic (e.g. just 'closed //SIM').
"""
import re

RULES = [  # order matters: first match wins
    ("Order Change & Cancellation", r"address (update|chang)|change.{0,10}address|cancel(l)?(ation)? order|cancel order|order cancel"),
    ("Product Enquiry", r"product enquiry|pre-?sales|spec sheet|compatib"),
    ("Billing & Payments", r"payment debited|double charge|duplicate (payment|txn|charge)|dup payment|charged twice|failed payment|payment fail|gst|invoice|coupon|discount|price adj|promo"),
    ("Account & Login", r"\botp\b|log ?in|password|account (locked|unlock)|e-?mail change|account"),
    ("Warranty & Repair", r"warranty claim|rma\b|repair request|out of warranty|in-warranty"),
    ("Returns & Refunds", r"refund (pending|approved|delay)|reverse pk?up|pickup missed|transit damage|return pickup|return request|return (rcvd|received)|qc (ok|pass)|refund status|refund delay|return refund"),
    ("App & Firmware", r"firmware|\bfw\b|\bapp\b|app crash|update fail"),
    ("Audio Quality", r"crackl|distort|low volume|volume low|mic|no sound|one side|audio|static|hiss|sound"),
    ("Charging & Battery", r"not charging|no charge|charg|battery|drain|case (led )?dead|case dead"),
    ("Connectivity", r"pair|bluetooth|\bbt\b|disconnect|connect(ivity)?|wifi|wi-fi|drop"),
    ("Delivery & Shipping", r"not deliver|not rcvd|not received|shipment|awb|courier|crr partner|rto|dlvry|delivery|lost in transit|parcel"),
]


def _segments(note: str):
    """Split a closing note into its parts; the issue is stated first, the fix comes later
    (e.g. 'pairing failure | advised fw update'), so firmware etc. in the fix must not count."""
    n = (note or "").lower().replace("\\n", "\n")
    m = re.search(r"issue:\s*([^|\n>]*?)(?:\s*(?:\||->|\.\s|\n|//)|$)", n)
    segs = []
    if m:
        segs.append(m.group(1))
    segs += [x.strip() for x in re.split(r"\||->|\.\s|\n|//| - ", n) if x.strip()]
    return segs[:3]


def label_from_note(note: str):
    for seg in _segments(note):
        for label, pat in RULES:
            if re.search(pat, seg):
                return label
    return None
