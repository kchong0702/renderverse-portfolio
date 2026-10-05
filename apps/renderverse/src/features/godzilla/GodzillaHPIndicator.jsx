import { IoEnter } from "react-icons/io5";
import Indicator from "../../ui/indicator/Indicator";

export default function GodzillaHPIndicator() {
  return (
    <>
      <Indicator
        settings={{
          position: [-0.8, 11.3, -7.3],
          rotation: [0, 0, 0],
          icon: <IoEnter size={25} />,
          id: "figurineEnterIndicator",
        }}
      />
    </>
  );
}
