"""The label set used everywhere (LLM prompt, classifier, charts)."""
CATEGORIES = [
    "Delivery & Shipping",        # not delivered / delayed / lost / tracking stuck (even if customer says 'paid')
    "Order Change & Cancellation",  # cancel order, change delivery address (before it arrives)
    "Billing & Payments",         # double charge, failed payment, GST invoice, coupon/discount/price
    "Returns & Refunds",          # return pickup, refund status/amount for a product being returned
    "Warranty & Repair",          # customer explicitly asks for warranty/repair/RMA
    "Connectivity",               # bluetooth/pairing/wifi/disconnecting
    "Charging & Battery",         # won't charge, case dead, battery drain
    "Audio Quality",              # crackling, low volume, mic, distortion, one side silent
    "App & Firmware",             # app crash, firmware update failed, app login to device features
    "Account & Login",            # OTP, password, account locked, email change
    "Product Enquiry",            # pre-sales: compatibility, features, 'will it survive a shower'
    "Other",                      # genuinely none of the above
]
