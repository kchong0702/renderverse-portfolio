import { useEffect, useMemo } from "react";
import type { MeshStandardMaterial, Texture } from "three";

export const useEnvMaterials = <T extends Record<string, MeshStandardMaterial>>(
  gltfMaterials: T,
  envMap?: Texture | null,
  envMapIntensity = 1,
): T => {
  const materials = useMemo(() => {
    if (!envMap) return gltfMaterials;
    return Object.fromEntries(
      Object.entries(gltfMaterials).map(([name, material]) => {
        const clone = material.clone();
        clone.envMap = envMap;
        return [name, clone];
      }),
    ) as T;
  }, [gltfMaterials, envMap]);

  const isCloned = materials !== gltfMaterials;

  useEffect(() => {
    if (!isCloned) return;
    for (const material of Object.values(materials))
      material.envMapIntensity = envMapIntensity;
  }, [materials, isCloned, envMapIntensity]);

  useEffect(() => {
    if (!isCloned) return;
    return () => Object.values(materials).forEach((m) => m.dispose());
  }, [materials, isCloned]);

  return materials;
};
