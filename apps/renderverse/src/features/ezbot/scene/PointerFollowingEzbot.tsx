import { useRef } from "react";
import type * as THREE from "three";
import EzbotModel, {
  type EzbotModelProps,
} from "@/experience/models/EzbotModel";
import { useHeadFollowsPointer } from "./useHeadFollowsPointer";

export default function PointerFollowingEzbot(props: EzbotModelProps) {
  const head = useRef<THREE.Group>(null);
  useHeadFollowsPointer(head);
  return <EzbotModel {...props} headRef={head} />;
}
