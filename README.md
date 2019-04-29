## Query and download 1000 Genomes gVCF located on figshare

Author: Sean Cho (sean.cho@jhmi.edu)
Version: 0.10.0

These scripts query and download gVCF files reprocessed from 1000 Genomes low depth
WGS data located on [figshare](https://figshare.com/collections/1000_Genomes_gVCFs/4414307).
There are a total of 2,530 gVCFs aligned to the hs37d5 genome, processed using
[Sentieon tools](http://www.sentieon.com/), which are comparable to and compatible with GATK.
The complete data set is a little more than 14TB in size.

By default, a cache of the metadata for the gVCFs will be downloaded and stored as
a `pickle` dictionary at `~/.figshare/onekg_dict.pickle`. This will speed up future
queries and downloads.

### Requirements

The script is written in Python3 and uses the `requests` module.

### Installation

Simply clone the repository.

```
git clone git@github.com:sean-cho/figshare_onekg.git
```

### Usage

#### Queries

The argument `--no-download` will return a JSON file onto `stdout` containing all
the files matching your query. It is advisable to query first and see how many files
you will be downloading.

```
python3 figshare_onekg.py --no-download
```

#### Download all files

By default, the script downloads all the gVCFs. Do keep in mind though that there
are 14TB of data, and it is likely that you will need ~30 for your purposes.

```
python3 figshare_onekg.py
```

#### Download n files

You can also specify the number of files to download.

```
python3 figshare_onekg.py -n 10
```

#### Filter

You can filter for gVCFs with three parameters; sex, population, and superpopulation.
Codes for population and superpopulation are available [at the 1000 Genomes website](http://www.internationalgenome.org/category/population).

The query logic is: `(sex) AND (population OR superpopulation)`

```
### get all females of FIN population
python3 figshare_onekg.py -s female -p FIN

### get all AFR and IBS
python3 figshare_onekg.py -p IBS -sp AFR
```

### Changelog

```
20190428: v0.10.0: init. basic implementation.
```