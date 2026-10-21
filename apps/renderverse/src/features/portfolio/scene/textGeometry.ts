import { extend, type BufferGeometryNode } from "@react-three/fiber";
import { TextGeometry } from "three/examples/jsm/geometries/TextGeometry.js";

extend({ TextGeometry });

declare module "@react-three/fiber" {
  interface ThreeElements {
    textGeometry: BufferGeometryNode<TextGeometry, typeof TextGeometry>;
  }
}
