#include <iostream>

#include "bsoncxx/builder/basic/array.hpp"
#include "bsoncxx/builder/basic/document.hpp"
#include "bsoncxx/builder/basic/kvp.hpp"
#include "bsoncxx/types.hpp"
#include "bsoncxx/json.hpp"

#include "json.hpp"

#include "tbb/tbb.h"

#include "mongo.hpp"
#include "logger.hpp"
#include "pipeline.hpp"

int main()
{
    try
    {
        // ----------从数据库读取数据----------
        auto read_data = [](const std::string &db_name, const std::string &coll_name)
        {
            auto results_cursor = MONGO.get_db(db_name)[coll_name].find({});
            std::vector<nlohmann::json> results;
            for (auto &&ch : results_cursor)
            {
                nlohmann::json m_json = nlohmann::json::parse(bsoncxx::to_json(ch));
                results.emplace_back(m_json);
            }
            return results;
        };
        auto form_results = read_data("ods", "submissionmodels");
        // ----------组织成二维表格的形式----------

        // 获取单选中的值
        auto get_swich_label = [](const nlohmann::json &input_json)
        {
            auto temp_id = input_json["value"]["value"][0];
            for (const auto &ch_ : input_json["properties"]["choices"])
            {
                if (ch_["id"] == temp_id)
                {
                    return ch_["label"];
                }
            }
            throw std::logic_error("解析时未找到值");
        };
        // 获取是否中的值
        auto get_yesno_label = [](const nlohmann::json &input_json)
        {
            auto temp_id = input_json["value"];
            for (const auto &ch_ : input_json["properties"]["choices"])
            {
                if (ch_["id"] == temp_id)
                {
                    return ch_["label"];
                }
            }
            throw std::logic_error("解析时未找到值");
        };
        // 处理集合中单个文档的数据
        std::vector<bsoncxx::document::value> visitor_submit;
        std::vector<bsoncxx::document::value> visitor_submit_accompany;
        std::vector<bsoncxx::document::value> visitor_submit_tutelage;
        auto data_process = [&](const tbb::blocked_range<size_t> &range)
        {
            for (size_t index = range.begin(); index != range.end(); ++index)
            {
                nlohmann::json input_json = form_results[index];
                nlohmann::json results_json;
                std::vector<nlohmann::json> accompany_json;
                std::vector<nlohmann::json> tutelage_json;
                results_json["提交日期"] = input_json["updatedAt"];
                results_json["fid"] = input_json["_id"];
                for (const auto &ch : input_json["answers"])
                {
                    if (ch["title"] == "请输入您的姓名")
                    {
                        results_json["提交人姓名"] = ch["value"];
                    }
                    else if (ch["title"] == "请输入您的身份证号")
                    {
                        results_json["提交人身份证号"] = ch["value"];
                    }
                    else if (ch["title"] == "请输入您的联系方式")
                    {
                        results_json["提交人电话号"] = ch["value"];
                    }
                    else if (ch["title"] == "请输入您的公司名称")
                    {
                        results_json["提交人所属公司"] = ch["value"];
                    }
                    else if (ch["title"] == "请选择您的作业地点")
                    {
                        results_json["作业地点"] = get_swich_label(ch);
                    }
                    else if (ch["title"] == "请输入您此次入场的作业人数")
                    {
                        results_json["作业人数"] = ch["value"];
                    }
                    else if (ch["title"] == "请输入您的计划开完工时间")
                    {
                        results_json["计划开工时间"] = ch["value"]["start"];
                        results_json["计划完工时间"] = ch["value"]["end"];
                    }
                    else if (ch["title"] == "请选择您的作业内容大类")
                    {
                        results_json["作业内容大类"] = get_swich_label(ch);
                    }
                    else if (ch["title"] == "请选择作业内容细分")
                    {
                        results_json["作业内容细分"] = get_swich_label(ch);
                    }
                    else if (ch["title"] == "请选择作业危险性，请仔细选择")
                    {
                        results_json["作业危险性"] = get_swich_label(ch);
                    }
                    else if (ch["title"] == "是否需要特殊权限申请")
                    {
                        results_json["是否需要特殊权限申请"] = get_yesno_label(ch);
                    }
                    else if (ch["title"] == "随行人员明细")
                    {
                        if (ch["value"].is_array())
                        {
                            size_t index = 0;
                            for (const auto &ch_ : ch["value"])
                            {
                                nlohmann::json temp;
                                temp["fid"] = input_json["_id"];
                                for (const auto &ch__ : ch_.items())
                                {
                                    auto temp_id = ch__.key();
                                    std::string temp_label;
                                    for (const auto &ch____ : ch["properties"]["tableColumns"])
                                    {
                                        if(ch____["id"] == temp_id)
                                        {
                                            temp_label = ch____["label"];
                                            break;
                                        }
                                    }
                                    temp[temp_label] = ch["value"][index][ch__.key()];
                                }
                                tutelage_json.emplace_back(temp);
                                index++;
                            }
                        }
                    }
                    else if (ch["title"] == "监护人明细")
                    {
                        if (ch["value"].is_array())
                        {
                            size_t index = 0;
                            for (const auto &ch_ : ch["value"])
                            {
                                nlohmann::json temp;
                                temp["fid"] = input_json["_id"];
                                for (const auto &ch__ : ch_.items())
                                {
                                    auto temp_id = ch__.key();
                                    std::string temp_label;
                                    for (const auto &ch____ : ch["properties"]["tableColumns"])
                                    {
                                        if(ch____["id"] == temp_id)
                                        {
                                            temp_label = ch____["label"];
                                            break;
                                        }
                                    }
                                    temp[temp_label] = ch["value"][index][ch__.key()];
                                }
                                tutelage_json.emplace_back(temp);
                                index++;
                            }
                        }
                    }
                }
                // 插入数据
                visitor_submit.emplace_back(bsoncxx::from_json(results_json.dump()));
                for (const auto &ch : accompany_json)
                {
                    visitor_submit_accompany.emplace_back(bsoncxx::from_json(ch.dump()));
                }
                for (const auto &ch : tutelage_json)
                {
                    visitor_submit_accompany.emplace_back(bsoncxx::from_json(ch.dump()));
                }
            }
        };
        // 利用tbb加速
        tbb::parallel_for(tbb::blocked_range<size_t>((size_t)0, form_results.size()), data_process);
        // ----------写入数据库----------
        if(!visitor_submit.empty())
        {
            auto m_coll = MONGO.get_coll("dm", "visitor_submit");
            m_coll.insert_many(visitor_submit);
            if(!visitor_submit_accompany.empty())
            {
                auto m_coll_a = MONGO.get_coll("dm", "visitor_submit_accompany");
                m_coll_a.insert_many(visitor_submit_accompany);
            }
            if(!visitor_submit_tutelage.empty())
            {
                auto m_coll_t = MONGO.get_coll("dm", "visitor_submit_tutelage");
                m_coll_t.insert_many(visitor_submit_tutelage);
            }
        }
        std::cout << "hello" << std::endl;
    }
    catch (const std::exception &e)
    {
        std::cerr << e.what() << '\n';
    }
    return 0;
}
