export type Language = "ar" | "en";

type Copy = {
  appName: string;
  language: string;
  arabic: string;
  english: string;
  createTitle: string;
  createDescription: string;
  messageLabel: string;
  messagePlaceholder: string;
  expiresLabel: string;
  create: string;
  creating: string;
  emptyMessage: string;
  generalError: string;
  rateLimitedTitle: string;
  rateLimitedDescription: string;
  successTitle: string;
  successDescription: string;
  copy: string;
  copied: string;
  copyFailed: string;
  share: string;
  shareLinkLabel: string;
  nativeShareUnavailable: string;
  revealChecking: string;
  revealTitle: string;
  revealDescription: string;
  unavailableTitle: string;
  unavailableDescription: string;
  revealErrorTitle: string;
  revealErrorDescription: string;
  sendOwnTitle: string;
  sendOwnAction: string;
  sentWith: string;
  footer: string;
  duration: Record<"1" | "5" | "15" | "60" | "1440", string>;
  advancedOptions: string;
  secretCodeLabel: string;
  secretCodeDescription: string;
  secretCodePlaceholder: string;
  secretCodeTooShort: string;
  destroyOnOpenLabel: string;
  destroyOnOpenDescription: string;
  secretCodePromptTitle: string;
  secretCodePromptDescription: string;
  secretCodeRequired: string;
  secretCodeInvalid: string;
  secretCodeThrottled: string;
  unlock: string;
  unlocking: string;
  cancelCodeTitle: string;
  cancelCodeDescription: string;
  copyCancelCode: string;
  cancelCodeCopied: string;
  cancelCodeCopyFailed: string;
  cancelLinkAction: string;
  cancelTitle: string;
  cancelDescription: string;
  cancelReferenceLabel: string;
  cancelReferenceDescription: string;
  cancelReferencePlaceholder: string;
  cancelReferenceError: string;
  cancelCodeLabel: string;
  cancelCodePlaceholder: string;
  cancelCodeRequired: string;
  cancelAction: string;
  cancelling: string;
  cancelUnavailable: string;
  cancelThrottled: string;
  cancelSuccessTitle: string;
  cancelSuccessDescription: string;
  cancelBackToCreate: string;
  cancelExistingTitle: string;
  cancelExistingDescription: string;
};

export const copy: Record<Language, Copy> = {
  ar: {
    appName: "OneSecret",
    language: "اللغة",
    arabic: "العربية",
    english: "English",
    createTitle: "أرسل رسالة تختفي بعد قراءتها",
    createDescription: "اكتب الرسالة، اختر المدة، ثم أرسل الرابط.",
    messageLabel: "رسالتك",
    messagePlaceholder: "اكتب رسالتك هنا…",
    expiresLabel: "مدة بقاء الرابط",
    create: "إنشاء الرابط",
    creating: "جارٍ إنشاء الرابط…",
    emptyMessage: "اكتب رسالة أولًا.",
    generalError: "تعذر إنشاء الرابط الآن. حاول مرة أخرى.",
    rateLimitedTitle: "حاول بعد قليل",
    rateLimitedDescription: "هناك محاولات كثيرة الآن. انتظر قليلًا ثم حاول مرة أخرى.",
    successTitle: "الرابط جاهز",
    successDescription: "أرسله للشخص الذي تريد.",
    copy: "نسخ الرابط",
    copied: "تم نسخ الرابط.",
    copyFailed: "انسخ الرابط يدويًا.",
    share: "مشاركة",
    shareLinkLabel: "رابط المشاركة المختصر",
    nativeShareUnavailable: "المشاركة من الجهاز غير متاحة هنا. انسخ الرابط لمشاركته.",
    revealChecking: "جارٍ فتح الرسالة…",
    revealTitle: "رسالتك",
    revealDescription: "اقرأها الآن.",
    unavailableTitle: "هذا الرابط غير متاح",
    unavailableDescription: "قد يكون قد استُخدم أو انتهت صلاحيته.",
    revealErrorTitle: "تعذر فتح الرسالة",
    revealErrorDescription: "حاول مرة أخرى لاحقًا.",
    sendOwnTitle: "هل تريد إرسال رسالة خاصة؟",
    sendOwnAction: "أرسل رسالتك الآمنة",
    sentWith: "أُرسلت بأمان عبر OneSecret",
    footer: "Alhareith Aldahia",
    duration: { "1": "دقيقة واحدة", "5": "5 دقائق", "15": "15 دقيقة", "60": "ساعة", "1440": "24 ساعة" },
    advancedOptions: "خيارات إضافية",
    secretCodeLabel: "Secret Code اختياري",
    secretCodeDescription: "سيُطلب من المستلم قبل عرض الرسالة.",
    secretCodePlaceholder: "8 أحرف أو أكثر",
    secretCodeTooShort: "يجب أن يتكون Secret Code من 8 أحرف على الأقل.",
    destroyOnOpenLabel: "إتلاف بعد أول فتح",
    destroyOnOpenDescription: "اجعله لمرة واحدة بدل بقائه حتى انتهاء المدة.",
    secretCodePromptTitle: "أدخل Secret Code",
    secretCodePromptDescription: "هذه الرسالة محمية بكود من المرسل.",
    secretCodeRequired: "أدخل Secret Code أولًا.",
    secretCodeInvalid: "Secret Code غير صحيح أو تعذر فتح الرسالة.",
    secretCodeThrottled: "تمت محاولات كثيرة. انتظر قليلًا ثم حاول مرة أخرى.",
    unlock: "فتح الرسالة",
    unlocking: "جارٍ الفتح…",
    cancelCodeTitle: "رمز إلغاء الرابط",
    cancelCodeDescription: "رمز من خمسة أحرف أو أرقام واضحة. احفظه الآن ولا ترسله مع الرابط.",
    copyCancelCode: "نسخ رمز الإلغاء",
    cancelCodeCopied: "تم نسخ رمز الإلغاء.",
    cancelCodeCopyFailed: "انسخ رمز الإلغاء يدويًا واحفظه في مكان آمن.",
    cancelLinkAction: "إلغاء رابط لاحقًا",
    cancelTitle: "إلغاء رابط رسالة",
    cancelDescription: "ألصق الرابط وأدخل رمز الإلغاء الذي حفظته.",
    cancelReferenceLabel: "رابط الرسالة أو معرّفها",
    cancelReferenceDescription: "يُستخرج المعرّف داخل المتصفح قبل إرسال طلب الإلغاء.",
    cancelReferencePlaceholder: "https://…/s/…",
    cancelReferenceError: "أدخل رابط رسالة صحيحًا أو معرّفًا صالحًا.",
    cancelCodeLabel: "رمز الإلغاء",
    cancelCodePlaceholder: "مثال: A7K2Z",
    cancelCodeRequired: "أدخل رمز الإلغاء المكون من خمسة رموز.",
    cancelAction: "إلغاء الرابط",
    cancelling: "جارٍ إلغاء الرابط…",
    cancelUnavailable: "تعذر إلغاء هذا الرابط. تحقق من البيانات ثم حاول مرة أخرى.",
    cancelThrottled: "تمت محاولات كثيرة. انتظر قليلًا ثم حاول مرة أخرى.",
    cancelSuccessTitle: "تم إلغاء الرابط",
    cancelSuccessDescription: "لن يعود الرابط متاحًا لفتح الرسالة.",
    cancelBackToCreate: "إنشاء رسالة جديدة",
    cancelExistingTitle: "إلغاء رابط موجود",
    cancelExistingDescription: "ألصق الرابط وأدخل رمز الإلغاء الذي حفظته.",
  },
  en: {
    appName: "OneSecret",
    language: "Language",
    arabic: "العربية",
    english: "English",
    createTitle: "Send a message that disappears after it is read",
    createDescription: "Write the message, choose a time, then send the link.",
    messageLabel: "Your message",
    messagePlaceholder: "Write your message here…",
    expiresLabel: "Link expiry",
    create: "Create link",
    creating: "Creating link…",
    emptyMessage: "Write a message first.",
    generalError: "The link could not be created. Please try again.",
    rateLimitedTitle: "Please try again shortly",
    rateLimitedDescription: "There are too many attempts right now. Please wait and try again.",
    successTitle: "Your link is ready",
    successDescription: "Send it to the person you choose.",
    copy: "Copy link",
    copied: "Link copied.",
    copyFailed: "Copy the link manually.",
    share: "Share",
    shareLinkLabel: "Shortened share link",
    nativeShareUnavailable: "Native sharing is unavailable here. Copy the link to share it.",
    revealChecking: "Opening your message…",
    revealTitle: "Your message",
    revealDescription: "Read it now.",
    unavailableTitle: "This link is unavailable",
    unavailableDescription: "It may have been used or expired.",
    revealErrorTitle: "The message could not be opened",
    revealErrorDescription: "Please try again later.",
    sendOwnTitle: "Want to send a private message?",
    sendOwnAction: "Send your own secure message",
    sentWith: "Sent securely with OneSecret",
    footer: "Alhareith Aldahia",
    duration: { "1": "1 minute", "5": "5 minutes", "15": "15 minutes", "60": "1 hour", "1440": "24 hours" },
    advancedOptions: "Optional settings",
    secretCodeLabel: "Optional Secret Code",
    secretCodeDescription: "The recipient must enter it before viewing the message.",
    secretCodePlaceholder: "8 characters or more",
    secretCodeTooShort: "The Secret Code must have at least 8 characters.",
    destroyOnOpenLabel: "Destroy after first open",
    destroyOnOpenDescription: "Make this one-time only instead of keeping it until expiry.",
    secretCodePromptTitle: "Enter Secret Code",
    secretCodePromptDescription: "The sender protected this message with a code.",
    secretCodeRequired: "Enter the Secret Code first.",
    secretCodeInvalid: "The Secret Code is invalid or the message cannot be opened.",
    secretCodeThrottled: "Too many attempts. Please wait and try again.",
    unlock: "Open message",
    unlocking: "Opening…",
    cancelCodeTitle: "Link cancellation code",
    cancelCodeDescription: "Five clear letters or numbers. Save it now and do not send it with the link.",
    copyCancelCode: "Copy cancellation code",
    cancelCodeCopied: "Cancellation code copied.",
    cancelCodeCopyFailed: "Copy the cancellation code manually and keep it somewhere safe.",
    cancelLinkAction: "Cancel a link later",
    cancelTitle: "Cancel a message link",
    cancelDescription: "Paste the link and enter the cancellation code you saved.",
    cancelReferenceLabel: "Message link or identifier",
    cancelReferenceDescription: "The identifier is extracted in this browser before the cancellation request is sent.",
    cancelReferencePlaceholder: "https://…/s/…",
    cancelReferenceError: "Enter a valid message link or identifier.",
    cancelCodeLabel: "Cancellation code",
    cancelCodePlaceholder: "Example: A7K2Z",
    cancelCodeRequired: "Enter the five-symbol cancellation code.",
    cancelAction: "Cancel link",
    cancelling: "Cancelling link…",
    cancelUnavailable: "This link could not be cancelled. Check the details and try again.",
    cancelThrottled: "Too many attempts. Please wait and try again.",
    cancelSuccessTitle: "Link cancelled",
    cancelSuccessDescription: "The link can no longer open the message.",
    cancelBackToCreate: "Create a new message",
    cancelExistingTitle: "Cancel an existing link",
    cancelExistingDescription: "Paste the link and enter the cancellation code you saved.",
  },
};
