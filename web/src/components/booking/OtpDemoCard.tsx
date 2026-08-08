import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";

export function OtpDemoCard() {
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [ref, setRef] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const send = async () => {
    if (!phone.trim()) return;
    setBusy(true);
    try {
      const res = await api.sendOtp(phone.trim());
      setRef(res.ref);
      toast.success("OTP sent", { description: `Ref ${res.ref}` });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Couldn't send the OTP");
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    if (!ref || !code.trim()) return;
    setBusy(true);
    try {
      const res = await api.verifyOtp(ref, code.trim());
      if (res.verified) toast.success("Phone verified");
      else toast.error(res.error ?? "Incorrect code");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Couldn't verify the code");
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="rounded-xl border border-border bg-surface/60 p-4">
      <div className="flex items-center gap-2">
        <h3 className="font-display text-sm font-semibold text-muted-foreground">
          Phone verification
        </h3>
        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
          Demo
        </span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        Optional — this does not affect your booking.
      </p>

      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <Input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="+8801XXXXXXXXX"
          inputMode="tel"
          className="h-9 text-sm"
        />
        <Button
          variant="secondary"
          size="sm"
          className="h-9 shrink-0"
          disabled={busy || !phone.trim()}
          onClick={send}
        >
          Send code
        </Button>
      </div>

      {ref && (
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <Input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="6-digit code"
            inputMode="numeric"
            className="h-9 text-sm"
          />
          <Button
            variant="secondary"
            size="sm"
            className="h-9 shrink-0"
            disabled={busy || !code.trim()}
            onClick={verify}
          >
            Verify
          </Button>
        </div>
      )}
    </aside>
  );
}
