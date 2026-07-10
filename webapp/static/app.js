(function () {
    const state = window.__HYPERAUTH_STATE__ || {};
    const telegram = window.Telegram?.WebApp || null;
    let rulesLoaded = false;
    let submitting = false;

    if (telegram) {
        telegram.ready();
        telegram.expand();

        const root = document.documentElement;
        const theme = telegram.themeParams || {};

        if (theme.bg_color) {
            root.style.setProperty("--bg", theme.bg_color);
        }

        if (theme.text_color) {
            root.style.setProperty("--text", theme.text_color);
        }

        root.style.setProperty(
            "--surface",
            theme.secondary_bg_color || theme.bg_color || "#ffffff"
        );

        if (theme.hint_color) {
            root.style.setProperty("--muted", theme.hint_color);
        }

        if (theme.button_text_color) {
            root.style.setProperty("--accent-text", theme.button_text_color);
        }
    }

    function setupAvatar() {
        const avatar = document.getElementById("bot-avatar");

        if (!avatar) {
            return;
        }

        const fallbackLabel = avatar.dataset.fallbackLabel || "HA";

        function showFallback() {
            avatar.style.backgroundImage = "none";
            avatar.textContent = fallbackLabel;
            avatar.classList.remove("has-image");
        }

        showFallback();

        if (!state.avatarUrl) {
            return;
        }

        const preload = new Image();
        preload.onload = function () {
            avatar.style.backgroundImage = `url("${state.avatarUrl}")`;
            avatar.textContent = "";
            avatar.classList.add("has-image");
        };
        preload.onerror = function () {
            showFallback();
        };
        preload.src = state.avatarUrl;
    }

    function setupErrorMessage() {
        const errorText = document.getElementById("error-text");

        if (errorText && typeof state.errorMessage === "string" && state.errorMessage.trim()) {
            errorText.textContent = state.errorMessage;
        }
    }

    function showPage(id) {
        document.querySelectorAll(".page").forEach((page) => {
            page.classList.remove("active");
        });

        const target = document.getElementById(id);

        if (target) {
            target.classList.add("active");
        }
    }

    async function sendResult(action) {
        if (submitting) {
            return;
        }

        submitting = true;
        document.body.classList.add("is-submitting");
        console.log("Submitting verification:", action);

        try {
            const initData = telegram?.initData || "";
            const response = await fetch("/api/verify", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    token: state.token,
                    action: action,
                    initData: initData,
                }),
            });

            const contentType = response.headers.get("content-type") || "";
            const result = contentType.includes("application/json")
                ? await response.json()
                : { ok: false, message: await response.text() };

            console.log("Verification result:", result);

            if (response.ok && result.ok) {
                showSuccess();

                if (telegram) {
                    telegram.showAlert(
                        action === "agree"
                            ? "Verification completed successfully."
                            : "Verification declined."
                    );

                    setTimeout(() => {
                        telegram.close();
                    }, 1000);
                }

                return;
            }

            showMessage(getErrorMessage(result, response.status));
        } catch (error) {
            console.error(error);

            showMessage("Unable to communicate with verification server.");
        } finally {
            submitting = false;
            document.body.classList.remove("is-submitting");
        }
    }

    function showMessage(message) {
        if (telegram) {
            telegram.showAlert(message);
            return;
        }

        alert(message);
    }

    function getErrorMessage(result, status) {
        if (status === 422) {
            return "Verification request is missing Telegram data. Please reopen the Mini App.";
        }

        if (result && typeof result.message === "string" && result.message.trim()) {
            return result.message;
        }

        if (result && typeof result.detail === "string" && result.detail.trim()) {
            return result.detail;
        }

        if (result && Array.isArray(result.detail) && result.detail.length > 0) {
            const first = result.detail[0];
            if (typeof first === "string" && first.trim()) {
                return first;
            }

            if (first && typeof first.msg === "string" && first.msg.trim()) {
                return first.msg;
            }
        }

        return "Verification failed.";
    }

    function showSuccess() {
        const text = document.getElementById("success-text");

        if (text) {
            text.textContent = "Verification completed successfully.";
        }

        showPage("page-success");
    }

    function enableAgreeButton() {
        const button = document.getElementById("btn-agree");
        const hint = document.getElementById("scroll-hint");

        if (button) {
            button.disabled = false;
            button.classList.add("ready");
        }

        if (hint) {
            hint.style.display = "none";
        }
    }

    function loadRules() {
        if (rulesLoaded) {
            return;
        }

        rulesLoaded = true;
        const rules = document.getElementById("rules-content");

        if (!rules) {
            return;
        }

        rules.textContent =
            state.rules || "No specific rules have been set.";

        if (rules.scrollHeight <= rules.clientHeight + 1) {
            enableAgreeButton();
            return;
        }

        rules.addEventListener("scroll", function () {
            if (
                rules.scrollHeight - rules.scrollTop <=
                rules.clientHeight + 20
            ) {
                enableAgreeButton();
            }
        }, { passive: true });
    }

    const captchaButton = document.getElementById("btn-captcha");

    if (captchaButton) {
        captchaButton.addEventListener("click", function () {
            if (state.hasRules) {
                showPage("page-rules");
                loadRules();
                return;
            }

            sendResult("agree");
        });
    }

    const agreeButton = document.getElementById("btn-agree");

    if (agreeButton) {
        agreeButton.addEventListener("click", function () {
            sendResult("agree");
        });
    }

    const joinButton = document.getElementById("btn-join");

    if (joinButton) {
        joinButton.addEventListener("click", function () {
            sendResult("agree");
        });
    }

    setupErrorMessage();

    if (!state.token) {
        showPage("page-error");
    } else if (!state.captchaEnabled && !state.hasRules) {
        showPage("page-simple");
    } else if (!state.captchaEnabled && state.hasRules) {
        showPage("page-rules");
        loadRules();
    } else {
        showPage("page-captcha");
    }

    setupAvatar();

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            enableAgreeButton,
            loadRules,
            setupAvatar,
            sendResult,
            showPage,
        };
    }
})();
