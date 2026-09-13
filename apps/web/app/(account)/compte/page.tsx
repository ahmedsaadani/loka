"use client";

import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";

const ROLE_LABEL: Record<string, string> = {
  traveler: "Voyageur",
  host: "Propriétaire",
  staff: "Équipe Loka",
  admin: "Administrateur",
};

export default function AccountPage() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState({ first_name: "", last_name: "", phone: "" });
  const [password, setPassword] = useState({ current_password: "", new_password: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user)
      setForm({ first_name: user.first_name, last_name: user.last_name, phone: user.phone });
  }, [user]);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.patch("/auth/me/", form);
      await refreshUser();
      toast.success("Profil mis à jour.");
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Une erreur est survenue.");
    } finally {
      setSaving(false);
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post("/auth/password/change/", password);
      setPassword({ current_password: "", new_password: "" });
      toast.success("Mot de passe modifié.");
    } catch (err) {
      toast.error(
        err instanceof ApiRequestError
          ? (err.fieldError("current_password") ?? err.fieldError("new_password") ?? err.message)
          : "Une erreur est survenue.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (!user) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl">Mon profil</h1>
        <p className="text-muted-foreground">
          {user.email} · <Badge variant="secondary">{ROLE_LABEL[user.role]}</Badge>{" "}
          {user.is_identity_verified ? (
            <Badge variant="verified">Identité vérifiée</Badge>
          ) : (
            <Badge variant="muted">Identité non vérifiée</Badge>
          )}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Informations</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={saveProfile} className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="first_name">Prénom</Label>
              <Input
                id="first_name"
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="last_name">Nom</Label>
              <Input
                id="last_name"
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              />
            </div>
            <div className="space-y-1 sm:col-span-2">
              <Label htmlFor="phone">Téléphone</Label>
              <Input
                id="phone"
                type="tel"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={saving}>
                Enregistrer
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Mot de passe</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={changePassword} className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="current_password">Mot de passe actuel</Label>
              <Input
                id="current_password"
                type="password"
                autoComplete="current-password"
                value={password.current_password}
                onChange={(e) => setPassword({ ...password, current_password: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="new_password">Nouveau mot de passe (10 caractères min.)</Label>
              <Input
                id="new_password"
                type="password"
                autoComplete="new-password"
                minLength={10}
                value={password.new_password}
                onChange={(e) => setPassword({ ...password, new_password: e.target.value })}
              />
            </div>
            <div className="sm:col-span-2">
              <Button
                type="submit"
                variant="outline"
                disabled={saving || !password.current_password || password.new_password.length < 10}
              >
                Changer le mot de passe
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
