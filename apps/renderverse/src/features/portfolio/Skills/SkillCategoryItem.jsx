import Rating from "./Rating";
import PropTypes from "prop-types";

const SkillCategoryItem = ({ item }) => {
  const { name, rating } = item;
  return (
    <li>
      {name}
      <Rating size={12} checked={rating} />
    </li>
  );
};

SkillCategoryItem.propTypes = {
  item: PropTypes.object,
};

export default SkillCategoryItem;
