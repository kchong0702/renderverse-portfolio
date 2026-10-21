import { useEffect, useMemo } from "react";

export const useEnvMaterials = (gltfMaterials, envMap, envMapIntensity = 1) => {
  const materials = useMemo(() => {
    if (!envMap) return gltfMaterials;
    return Object.fromEntries(
      Object.entries(gltfMaterials).map(([name, material]) => {
        const clone = material.clone();
        clone.envMap = envMap;
        return [name, clone];
      }),
    );
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
