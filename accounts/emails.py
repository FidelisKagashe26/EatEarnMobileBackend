"""Branded transactional emails (OTP verification)."""
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

LOGO_PATH = Path(settings.BASE_DIR) / "static_assets" / "eatearn-logo.png"

BRAND_NAVY = "#0B1020"
BRAND_ORANGE = "#F97316"


def _otp_html(full_name: str, code: str, ttl_minutes: int) -> str:
    first_name = (full_name or "there").split(" ")[0]
    digits = "".join(
        f"<span style='display:inline-block;min-width:34px;padding:12px 6px;margin:0 3px;"
        f"background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;"
        f"font-size:26px;font-weight:700;color:{BRAND_NAVY};font-family:Consolas,monospace;'>{d}</span>"
        for d in code
    )
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#F2F5FA;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F2F5FA;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="420" cellpadding="0" cellspacing="0"
                 style="background:#FFFFFF;border-radius:16px;overflow:hidden;box-shadow:0 6px 18px rgba(15,23,42,0.08);">
            <tr>
              <td align="center" style="background:{BRAND_NAVY};padding:26px 24px 20px;">
                <img src="cid:eatearn-logo" alt="Eat &amp; Earn" width="180" style="display:block;max-width:180px;height:auto;" />
              </td>
            </tr>
            <tr>
              <td style="padding:28px 28px 8px;">
                <p style="margin:0;color:{BRAND_NAVY};font-size:18px;font-weight:700;">Hi {first_name}, 👋</p>
                <p style="margin:10px 0 0;color:#475569;font-size:14px;line-height:21px;">
                  Use this code to verify your <strong>Eat &amp; Earn</strong> account:
                </p>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:18px 28px;">{digits}</td>
            </tr>
            <tr>
              <td style="padding:0 28px 6px;">
                <p style="margin:0;color:#64748B;font-size:13px;line-height:20px;">
                  The code expires in <strong style="color:{BRAND_ORANGE};">{ttl_minutes} minutes</strong>.
                  If you didn't request it, you can safely ignore this email.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:22px 28px 26px;">
                <hr style="border:none;border-top:1px solid #E2E8F0;margin:0 0 14px;" />
                <p style="margin:0;color:#94A3B8;font-size:11px;line-height:17px;" align="center">
                  Eat &amp; Earn · UDOM Campus Food Ordering<br />
                  Order campus meals, track live, and get faster delivery.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def send_otp_email(user, code: str) -> None:
    """Send the branded verification email (raises on failure)."""
    ttl = settings.OTP_TTL_MINUTES
    text_body = (
        f"Hello {user.full_name},\n\n"
        f"Your Eat & Earn verification code is: {code}\n"
        f"It expires in {ttl} minutes.\n\n"
        "If you did not request this code, you can ignore this email."
    )

    message = EmailMultiAlternatives(
        subject="Your Eat & Earn verification code",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(_otp_html(user.full_name, code, ttl), "text/html")
    message.mixed_subtype = "related"

    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as fh:
            logo = MIMEImage(fh.read())
        logo.add_header("Content-ID", "<eatearn-logo>")
        logo.add_header("Content-Disposition", "inline", filename="eatearn-logo.png")
        message.attach(logo)

    message.send(fail_silently=False)
