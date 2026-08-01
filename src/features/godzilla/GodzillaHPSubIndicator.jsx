import { IoEnter } from "react-icons/io5";
import Indicator from "../../ui/indicator/Indicator";

export default function GodzillaHPSubIndicator() {
  return (
    <>
      <Indicator
        settings={{
          position: [-3.13, 3.5, 7.45],
          rotation: [0, 0, 0],
          icon: <IoEnter size={25} />,
          id: "figurineExitIndicator",
        }}
      />
    </>
  );
}
